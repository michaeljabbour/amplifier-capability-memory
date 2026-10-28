#!/usr/bin/env python3
"""Archive Project Memory schema 1; explicitly import records into a NEW native log.

Export is Python stdlib-only. It opens only a temporary DB/WAL copy through
SQLite, never the source or a legacy MemoryStore. Import uses the separately
installed native Memory/Data APIs and never changes storage implementation.
"""

from __future__ import annotations

import argparse
import base64
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import sqlite3
import tempfile

FORMAT = "project-memory-archive/1"
MAX_SOURCE_BYTES = 64_000_000
MAX_ARCHIVE_BYTES = 128_000_000
FTS_OBJECTS = {
    "memories_fts",
    "memories_fts_data",
    "memories_fts_idx",
    "memories_fts_content",
    "memories_fts_docsize",
    "memories_fts_config",
}
TABLES = {
    "memories": {
        "id",
        "category",
        "content",
        "importance",
        "source",
        "created_at",
        "last_accessed",
        "access_count",
        "metadata",
    },
    "raw_captures": {
        "id",
        "timestamp",
        "event_type",
        "raw_content",
        "signal_type",
        "confidence",
        "processed",
        "session_id",
    },
    "schema_meta": {"key", "value"},
}
DECLARED = {
    name: {
        column: (
            "INTEGER"
            if column in {"access_count", "processed"}
            or (name == "raw_captures" and column == "id")
            else "REAL"
            if column in {"importance", "confidence"}
            else "TEXT"
        )
        for column in columns
    }
    for name, columns in TABLES.items()
}


def canonical(value):
    return json.dumps(
        value, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode("ascii")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_digest(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1_000_000), b""):
            h.update(block)
    return h.hexdigest()


def source_state(source):
    paths = {
        "db": source,
        "wal": Path(str(source) + "-wal"),
        "shm": Path(str(source) + "-shm"),
    }
    if sum(p.stat().st_size for p in paths.values() if p.exists()) > MAX_SOURCE_BYTES:
        raise ValueError(
            "DB/WAL/SHM exceeds 64 MB; use a separately reviewed larger-store workflow"
        )
    states = {}
    for key, path in paths.items():
        if not path.exists():
            states[key] = {"exists": False, "bytes": 0, "sha256": None, "stat": None}
            continue
        before = path.stat()
        checksum = file_digest(path)
        after = path.stat()
        fields = ("st_size", "st_mtime_ns", "st_ino", "st_dev")
        if any(getattr(before, f) != getattr(after, f) for f in fields):
            raise ValueError(
                "Source file changed while hashing; quiesce readers/writers and retry"
            )
        states[key] = {
            "exists": True,
            "bytes": after.st_size,
            "sha256": checksum,
            "stat": {f: getattr(after, f) for f in fields},
        }
    return states


def encode(value):
    if value is None:
        return {"type": "null"}
    if isinstance(value, bytes):
        return {"type": "blob", "base64": base64.b64encode(value).decode("ascii")}
    if isinstance(value, str):
        return {"type": "text", "value": value}
    if type(value) is int:
        return {"type": "integer", "decimal": str(value)}
    if type(value) is float:
        return {"type": "real", "hex": value.hex()}
    raise ValueError("Unsupported SQLite value type")


def decode(cell):
    if not isinstance(cell, dict):
        raise ValueError("Invalid typed cell")
    kind = cell.get("type")
    if kind == "null" and set(cell) == {"type"}:
        return None
    if (
        kind == "text"
        and set(cell) == {"type", "value"}
        and isinstance(cell["value"], str)
    ):
        return cell["value"]
    if kind == "blob" and set(cell) == {"type", "base64"}:
        return base64.b64decode(cell["base64"], validate=True)
    if kind == "integer" and set(cell) == {"type", "decimal"}:
        value = int(cell["decimal"])
        if not -(2**63) <= value < 2**63 or str(value) != cell["decimal"]:
            raise ValueError("Noncanonical SQLite integer")
        return value
    if kind == "real" and set(cell) == {"type", "hex"}:
        value = float.fromhex(cell["hex"])
        if math.isnan(value) or value.hex() != cell["hex"]:
            raise ValueError("Noncanonical SQLite real")
        return value
    raise ValueError("Invalid typed cell")


def new_bytes(destination, data):
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise ValueError("Destination already exists; nothing was replaced")
    fd, temporary = tempfile.mkstemp(prefix=".memory-archive-", dir=destination.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(
            temporary, destination
        )  # Exclusive publication; never replace a raced target.
    finally:
        Path(temporary).unlink(missing_ok=True)


def export_archive(source, destination):
    source = Path(source).resolve()
    destination = Path(destination)
    if not source.is_file():
        raise ValueError("Source must be an explicitly selected existing SQLite file")
    if destination.exists() or destination.is_symlink():
        raise ValueError("Destination already exists; nothing was replaced")
    before = source_state(source)
    with tempfile.TemporaryDirectory(prefix="project-memory-snapshot-") as temporary:
        snapshot = Path(temporary) / "snapshot.db"
        shutil.copyfile(source, snapshot)
        if before["wal"]["exists"]:
            shutil.copyfile(Path(str(source) + "-wal"), Path(str(snapshot) + "-wal"))
        copied = source_state(snapshot)
        if any(
            any(
                copied[k][field] != before[k][field]
                for field in ("exists", "bytes", "sha256")
            )
            for k in ("db", "wal")
        ):
            raise ValueError(
                "Snapshot copy changed while reading; quiesce the writer and retry"
            )
        # mode=ro applies to the temporary copy. SQLite may maintain its SHM
        # there, never at the original source. immutable=1 would ignore WAL.
        connection = sqlite3.connect(snapshot.as_uri() + "?mode=ro", uri=True)
        try:
            connection.execute("PRAGMA query_only=ON")
            connection.execute("PRAGMA trusted_schema=OFF")
            connection.execute("BEGIN")
            if connection.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
                raise ValueError("SQLite snapshot integrity check failed")
            objects = connection.execute(
                "SELECT name,type FROM sqlite_master WHERE type IN ('table','view')"
            ).fetchall()
            if any(
                kind != "table"
                or (
                    name not in TABLES
                    and name not in FTS_OBJECTS
                    and not name.startswith("sqlite_")
                )
                for name, kind in objects
            ):
                raise ValueError(
                    "Unsupported schema objects; no partial archive is produced"
                )
            version = connection.execute(
                "SELECT value FROM schema_meta WHERE key = ?", ("version",)
            ).fetchall()
            if version != [("1",)]:
                raise ValueError(
                    "Unsupported project-memory schema; only schema_meta version 1 is accepted"
                )
            tables = {}
            for table, required in TABLES.items():
                # Table names are constants, not artifact-controlled SQL.
                columns = connection.execute(f'PRAGMA table_info("{table}")').fetchall()
                if required != {c[1] for c in columns} or any(
                    c[2].upper() != DECLARED[table][c[1]] for c in columns
                ):
                    raise ValueError("Unsupported columns for " + table)
                rows = [
                    [encode(v) for v in row]
                    for row in connection.execute(f'SELECT * FROM "{table}"')
                ]
                rows.sort(key=canonical)
                tables[table] = {
                    "columns": [
                        dict(
                            zip(
                                (
                                    "cid",
                                    "name",
                                    "declared_type",
                                    "not_null",
                                    "default_sql",
                                    "primary_key",
                                ),
                                c,
                            )
                        )
                        for c in columns
                    ],
                    "row_count": len(rows),
                    "rows": rows,
                }
        except sqlite3.Error as error:
            raise ValueError(
                "Unsupported or unreadable project-memory SQLite schema"
            ) from error
        finally:
            connection.close()
    if source_state(source) != before:
        raise ValueError(
            "Source DB/WAL changed during export; no artifact was published"
        )
    artifact = {
        "format": FORMAT,
        "schema_version": 1,
        "source": {"file_name": source.name, "files": before},
        "consistency": "Copied DB/WAL bytes matched; DB/WAL/SHM hashes and stat matched before/after. Quiescent source required; temporary mode=ro SQL snapshot.",
        "scope": "All rows/columns of memories, raw_captures, schema_meta; FTS/indexes and SQLite internals are not a full-database backup.",
        "tables": tables,
    }
    data = canonical(artifact) + b"\n"
    if len(data) > MAX_ARCHIVE_BYTES:
        raise ValueError("Archive exceeds 128 MB; no partial archive was published")
    validate_artifact(artifact)
    new_bytes(destination, data)
    return {
        "format": FORMAT,
        "archive_sha256": digest(data),
        "rows": {t: v["row_count"] for t, v in tables.items()},
        "source_db_wal_and_shm_unchanged": True,
    }


def validate_artifact(artifact):
    if not isinstance(artifact, dict) or set(artifact) != {
        "format",
        "schema_version",
        "source",
        "consistency",
        "scope",
        "tables",
    }:
        raise ValueError("Invalid archive envelope")
    if artifact.get("format") != FORMAT or artifact.get("schema_version") != 1:
        raise ValueError("Unsupported archive format/version")
    if not isinstance(artifact.get("tables"), dict) or set(artifact["tables"]) != set(
        TABLES
    ):
        raise ValueError("Archive must contain all three source tables")
    source = artifact.get("source", {})
    if not isinstance(source, dict) or set(source) != {"file_name", "files"}:
        raise ValueError("Invalid source identity envelope")
    if not isinstance(source.get("file_name"), str) or not source["file_name"]:
        raise ValueError("Missing source identity")
    files = source.get("files", {})
    if not isinstance(files, dict) or set(files) != {"db", "wal", "shm"}:
        raise ValueError("Missing source snapshot fingerprints")
    for state in files.values():
        if (
            not isinstance(state, dict)
            or type(state.get("exists")) is not bool
            or type(state.get("bytes")) is not int
            or state["bytes"] < 0
        ):
            raise ValueError("Invalid source fingerprint")
        if state["exists"]:
            if not isinstance(state.get("sha256"), str) or not re.fullmatch(
                "[0-9a-f]{64}", state["sha256"]
            ):
                raise ValueError("Invalid source checksum")
            if (
                not isinstance(state.get("stat"), dict)
                or set(state["stat"]) != {"st_size", "st_mtime_ns", "st_ino", "st_dev"}
                or any(type(v) is not int or v < 0 for v in state["stat"].values())
            ):
                raise ValueError("Invalid source stat identity")
        elif state["bytes"] or state.get("sha256") is not None:
            raise ValueError("Invalid absent-source fingerprint")
    if not files["db"]["exists"]:
        raise ValueError("Source database identity is required")
    for name, table in artifact["tables"].items():
        if not isinstance(table, dict) or set(table) != {
            "columns",
            "row_count",
            "rows",
        }:
            raise ValueError("Invalid table envelope")
        columns = table.get("columns")
        rows = table.get("rows")
        if not isinstance(columns, list) or not isinstance(rows, list):
            raise ValueError("Invalid table shape")
        if any(
            not isinstance(c, dict)
            or set(c)
            != {
                "cid",
                "name",
                "declared_type",
                "not_null",
                "default_sql",
                "primary_key",
            }
            for c in columns
        ):
            raise ValueError("Invalid column envelope")
        names = [c.get("name") for c in columns]
        if any(not isinstance(n, str) for n in names):
            raise ValueError("Invalid column name")
        if len(set(names)) != len(names) or TABLES[name] != set(names):
            raise ValueError("Missing or duplicate source columns")
        for index, column in enumerate(columns):
            expected_pk = (
                1 if column["name"] == ("key" if name == "schema_meta" else "id") else 0
            )
            if (
                not isinstance(column["declared_type"], str)
                or type(column["cid"]) is not int
                or column["cid"] != index
                or column["declared_type"].upper() != DECLARED[name][column["name"]]
                or type(column["not_null"]) is not int
                or column["not_null"] not in (0, 1)
                or type(column["primary_key"]) is not int
                or column["primary_key"] != expected_pk
                or not (
                    column["default_sql"] is None
                    or isinstance(column["default_sql"], str)
                )
            ):
                raise ValueError("Unsupported column schema")
        if type(table.get("row_count")) is not int or table["row_count"] != len(rows):
            raise ValueError("Source row count mismatch")
        for row in rows:
            if not isinstance(row, list) or len(row) != len(columns):
                raise ValueError("Source row width mismatch")
            for cell in row:
                if encode(decode(cell)) != cell:
                    raise ValueError("Noncanonical typed cell")
    meta = artifact["tables"]["schema_meta"]
    names = [c["name"] for c in meta["columns"]]
    versions = [
        decode(r[names.index("value")])
        for r in meta["rows"]
        if decode(r[names.index("key")]) == "version"
    ]
    if versions != ["1"]:
        raise ValueError("Archive schema version row mismatch")
    return artifact


def archival_records(artifact, archive_sha256):
    manifest = {k: v for k, v in artifact.items() if k != "tables"}
    manifest["tables"] = {
        name: {k: v for k, v in table.items() if k != "rows"}
        for name, table in artifact["tables"].items()
    }
    yield canonical(
        {
            "kind": "legacy-archive-manifest",
            "archive_sha256": archive_sha256,
            "semantic_status": "archival evidence, not adopted facts",
            "manifest": manifest,
        }
    ).decode("ascii")
    for name, table in artifact["tables"].items():
        keys = [i for i, column in enumerate(table["columns"]) if column["primary_key"]]
        for ordinal, row in enumerate(table["rows"]):
            yield canonical(
                {
                    "kind": "legacy-archive-row",
                    "archive_sha256": archive_sha256,
                    "schema_version": 1,
                    "table": name,
                    "ordinal": ordinal,
                    "source_keys": [row[i] for i in keys],
                    "columns": table["columns"],
                    "cells": row,
                    "semantic_status": "archival evidence, not adopted facts",
                }
            ).decode("ascii")


def import_archive(archive, destination, wing, room="legacy-archive"):
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise ValueError(
            "Import needs a NEW explicitly selected native log; existing stores are preserved"
        )
    if (
        not wing.startswith("legacy-archive/")
        or not wing[len("legacy-archive/") :].strip()
        or not room.strip()
    ):
        raise ValueError(
            "Use an explicit archival wing: legacy-archive/<name>, with a nonempty room"
        )
    with Path(archive).open("rb") as handle:
        data = handle.read(MAX_ARCHIVE_BYTES + 1)
    if len(data) > MAX_ARCHIVE_BYTES:
        raise ValueError("Archive exceeds 128 MB")
    artifact = validate_artifact(json.loads(data))
    archive_sha256 = digest(data)
    records = list(archival_records(artifact, archive_sha256))
    # Only this import operation needs Memory/Data. Export stays stdlib-only.
    from amplifier_module_tool_memory.store import NativeMemoryStore

    with tempfile.TemporaryDirectory(
        prefix=".memory-import-", dir=destination.parent
    ) as temporary:
        log = Path(temporary) / "archive.log"
        # Typed archive rows are opaque evidence. Do not generate semantic
        # passage derivatives while transferring them; all payloads fit under
        # the already enforced archive bound.
        store = NativeMemoryStore(
            path=str(log), record_access=False, passage_min_chars=MAX_ARCHIVE_BYTES + 1
        )
        refs = []
        try:
            for payload in records:
                refs.append(
                    store.file(
                        wing=wing,
                        room=room,
                        content=payload,
                        source="project-memory-archive:" + archive_sha256,
                        category="legacy-archive",
                    )
                )
        finally:
            store.close()
        reopened = NativeMemoryStore(path=str(log), record_access=False)
        try:
            recovered = [
                reopened.store.get_cell(ref, record_access=False).payload.decode(
                    "ascii"
                )
                for ref in refs
            ]
            if Counter(recovered) != Counter(records):
                raise ValueError(
                    "Native durable payload roundtrip failed; destination not published"
                )
        finally:
            reopened.close()
        os.link(log, destination)
    return {
        "format": "project-memory-import-receipt/1",
        "archive_sha256": archive_sha256,
        "source_rows": {t: v["row_count"] for t, v in artifact["tables"].items()},
        "archival_records": len(records),
        "wing": wing,
        "room": room,
        "native_log_sha256": file_digest(destination),
        "durable_payload_roundtrip": True,
        "semantic_status": "archival evidence only; no facts adopted or source stores migrated in place",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    export = sub.add_parser("export")
    export.add_argument("source", type=Path)
    export.add_argument("--out", required=True, type=Path)
    imp = sub.add_parser("import")
    imp.add_argument("archive", type=Path)
    imp.add_argument("--new-store", required=True, type=Path)
    imp.add_argument("--wing", required=True)
    imp.add_argument("--room", default="legacy-archive")
    args = parser.parse_args(argv)
    try:
        result = (
            export_archive(args.source, args.out)
            if args.operation == "export"
            else import_archive(args.archive, args.new_store, args.wing, args.room)
        )
    except (
        ValueError,
        OSError,
        ImportError,
        RuntimeError,
        KeyError,
        TypeError,
    ) as error:
        parser.exit(2, type(error).__name__ + ": " + str(error) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
