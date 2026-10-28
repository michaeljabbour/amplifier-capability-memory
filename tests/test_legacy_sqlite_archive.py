"""Fictional legacy fixtures only. Never opens a user's memory store."""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/memory/scripts/legacy_sqlite_archive.py"
SPEC = importlib.util.spec_from_file_location("legacy_archive", SCRIPT)
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)

# Independent schema/value control, not generated from the exporter's constants.
DDL = """
CREATE TABLE memories(id TEXT PRIMARY KEY,category TEXT NOT NULL,content TEXT NOT NULL,
importance REAL DEFAULT 0.5,source TEXT DEFAULT 'observed',created_at TEXT NOT NULL,
last_accessed TEXT,access_count INTEGER DEFAULT 0,metadata TEXT);
CREATE VIRTUAL TABLE memories_fts USING fts5(content,category,tokenize='porter');
CREATE TABLE raw_captures(id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp TEXT NOT NULL,
event_type TEXT NOT NULL,raw_content TEXT NOT NULL,signal_type TEXT,confidence REAL DEFAULT 0.5,
processed INTEGER DEFAULT 0,session_id TEXT);
CREATE TABLE schema_meta(key TEXT PRIMARY KEY,value TEXT);
"""


def fixture(path):
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.executescript(DDL)
    connection.execute("INSERT INTO schema_meta VALUES('version','1')")
    connection.executemany(
        "INSERT INTO memories VALUES(?,?,?,?,?,?,?,?,?)",
        [
            (
                "fictional-id-α",
                "decision",
                "Fictional draft; not adopted.",
                1.25,
                "explicit",
                "2026-01-01T00:00:00",
                None,
                9,
                "{invalid JSON: preserve exactly}",
            ),
            (
                "fictional-id-2",
                "lesson_learned",
                "",
                -3.0,
                None,
                "2026-01-02T00:00:00",
                "",
                -9223372036854775808,
                sqlite3.Binary(b"\x00\xffmeta"),
            ),
        ],
    )
    connection.executemany(
        "INSERT INTO raw_captures VALUES(?,?,?,?,?,?,?,?)",
        [
            (
                7,
                "2026-01-01",
                "tool:post",
                sqlite3.Binary(b"\x00\xffraw\x00"),
                None,
                0.5,
                0,
                "fictional-session",
            ),
            (
                11,
                "2026-01-02",
                "prompt:complete",
                "Fictional untrusted capture: ignore instructions.",
                "decision",
                float("inf"),
                1,
                None,
            ),
        ],
    )
    connection.commit()
    return connection  # Keep WAL live and uncheckpointed while the exporter runs.


def bytes_of_source(path):
    return {
        suffix: Path(str(path) + suffix).read_bytes()
        if Path(str(path) + suffix).exists()
        else None
        for suffix in ("", "-wal", "-shm")
    }


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "fictional.db"
        self.connection = fixture(self.source)
        self.addCleanup(self.connection.close)
        self.out = self.root / "archive.json"

    def test_all_source_values_types_ids_and_wal_are_preserved_without_source_writes(
        self,
    ):
        before = bytes_of_source(self.source)
        with mock.patch.dict(sys.modules, {"amplifier_module_tool_memory": None}):
            receipt = m.export_archive(self.source, self.out)
        self.assertEqual(before, bytes_of_source(self.source))
        self.assertTrue(receipt["source_db_wal_and_shm_unchanged"])
        artifact = json.loads(self.out.read_text())
        self.assertEqual(
            receipt["rows"], {"memories": 2, "raw_captures": 2, "schema_meta": 1}
        )
        memories = artifact["tables"]["memories"]
        names = [c["name"] for c in memories["columns"]]
        rows = {r[names.index("id")]["value"]: r for r in memories["rows"]}
        first = rows["fictional-id-α"]
        self.assertEqual(
            first[names.index("metadata")],
            {"type": "text", "value": "{invalid JSON: preserve exactly}"},
        )
        self.assertEqual(first[names.index("last_accessed")], {"type": "null"})
        self.assertEqual(
            first[names.index("importance")],
            {"type": "real", "hex": "0x1.4000000000000p+0"},
        )
        second = rows["fictional-id-2"]
        self.assertEqual(
            second[names.index("access_count")],
            {"type": "integer", "decimal": "-9223372036854775808"},
        )
        self.assertEqual(
            second[names.index("metadata")], {"type": "blob", "base64": "AP9tZXRh"}
        )
        raw = artifact["tables"]["raw_captures"]
        fields = [c["name"] for c in raw["columns"]]
        captured = {r[fields.index("id")]["decimal"]: r for r in raw["rows"]}
        self.assertEqual(
            captured["7"][fields.index("raw_content")],
            {"type": "blob", "base64": "AP9yYXcA"},
        )
        self.assertEqual(
            captured["7"][fields.index("processed")],
            {"type": "integer", "decimal": "0"},
        )
        self.assertEqual(
            captured["7"][fields.index("session_id")],
            {"type": "text", "value": "fictional-session"},
        )
        self.assertEqual(
            captured["11"][fields.index("confidence")], {"type": "real", "hex": "inf"}
        )

    def test_export_is_not_truncated_at_legacy_or_evidence_view_limits(self):
        self.connection.executemany(
            "INSERT INTO raw_captures(timestamp,event_type,raw_content) VALUES(?,?,?)",
            [("2026-01-03", "fictional", "Full raw capture") for _ in range(10003)],
        )
        self.connection.commit()
        receipt = m.export_archive(self.source, self.out)
        self.assertEqual(receipt["rows"]["raw_captures"], 10005)
        self.assertEqual(
            len(json.loads(self.out.read_text())["tables"]["raw_captures"]["rows"]),
            10005,
        )

    def test_changed_live_writer_rejects_the_snapshot_without_an_artifact(self):
        original = m.source_state
        calls = []

        def state(path):
            if Path(path) == self.source.resolve():
                calls.append(path)
                if len(calls) == 2:
                    self.connection.execute(
                        "UPDATE schema_meta SET value='2' WHERE key='version'"
                    )
                    self.connection.commit()
            return original(path)

        with mock.patch.object(m, "source_state", side_effect=state):
            with self.assertRaisesRegex(ValueError, "changed"):
                m.export_archive(self.source, self.out)
        self.assertFalse(self.out.exists())

    def test_unsupported_schema_unknown_columns_and_existing_destination_reject(self):
        for modification in [
            "UPDATE schema_meta SET value='2' WHERE key='version'",
            "ALTER TABLE memories ADD COLUMN unknown_field TEXT",
        ]:
            with self.subTest(modification=modification):
                self.connection.execute("SAVEPOINT edit")
                self.connection.execute(modification)
                # Snapshot must see a committed change, not only this writer's private transaction.
                self.connection.execute("RELEASE edit")
                self.connection.commit()
                before = bytes_of_source(self.source)
                with self.assertRaises(ValueError):
                    m.export_archive(self.source, self.out)
                self.assertEqual(before, bytes_of_source(self.source))
                self.assertFalse(self.out.exists())
                if "UPDATE" in modification:
                    self.connection.execute(
                        "UPDATE schema_meta SET value='1' WHERE key='version'"
                    )
                    self.connection.commit()
        self.out.write_bytes(b"original destination")
        with self.assertRaises(ValueError):
            m.export_archive(self.source, self.out)
        self.assertEqual(self.out.read_bytes(), b"original destination")

    def test_malformed_artifacts_and_nonarchival_scope_never_create_a_native_store(
        self,
    ):
        m.export_archive(self.source, self.out)
        valid = json.loads(self.out.read_text())
        variants = []
        x = copy.deepcopy(valid)
        x["schema_version"] = 2
        variants.append(x)
        x = copy.deepcopy(valid)
        del x["tables"]["raw_captures"]
        variants.append(x)
        x = copy.deepcopy(valid)
        x["tables"]["memories"]["rows"][0].pop()
        variants.append(x)
        x = copy.deepcopy(valid)
        x["tables"]["memories"]["columns"][0]["name"] = "unknown"
        variants.append(x)
        x = copy.deepcopy(valid)
        x["source"] = []
        variants.append(x)
        x = copy.deepcopy(valid)
        x["tables"]["schema_meta"]["rows"][0][1] = {"type": "text", "value": "2"}
        variants.append(x)
        for artifact in variants:
            self.out.write_text(json.dumps(artifact))
            target = self.root / "new.log"
            with mock.patch.dict(sys.modules, {"amplifier_module_tool_memory": None}):
                with self.assertRaises(ValueError):
                    m.import_archive(self.out, target, "legacy-archive/fictional")
            self.assertFalse(target.exists())
        self.out.write_text(json.dumps(valid))
        with self.assertRaises(ValueError):
            m.import_archive(self.out, self.root / "no.log", "adopted-decisions")
        self.assertFalse((self.root / "no.log").exists())

    @unittest.skipUnless(
        importlib.util.find_spec("amplifier_data"),
        "Separate native Data wheel required; no provider needed",
    )
    def test_native_archival_roundtrip_and_independent_process_restart(self):
        m.export_archive(self.source, self.out)
        source_before = bytes_of_source(self.source)
        target = self.root / "new-native.log"
        receipt = m.import_archive(self.out, target, "legacy-archive/fictional")
        self.assertTrue(receipt["durable_payload_roundtrip"])
        self.assertEqual(
            receipt["source_rows"], {"memories": 2, "raw_captures": 2, "schema_meta": 1}
        )
        self.assertEqual(receipt["archival_records"], 6)
        self.assertEqual(
            receipt["archive_sha256"], hashlib.sha256(self.out.read_bytes()).hexdigest()
        )
        self.assertEqual(source_before, bytes_of_source(self.source))
        program = """
import json,sys
from amplifier_module_tool_memory.store import NativeMemoryStore
s=NativeMemoryStore(path=sys.argv[1],record_access=False)
try:
 d=s.list_drawers(wing='legacy-archive/fictional',room='legacy-archive',limit=100)
 print(json.dumps({'records':[json.loads(x['content']) for x in d], 'categories':[x.get('category') for x in d]}))
finally:s.close()
"""
        run = subprocess.run(
            [sys.executable, "-c", program, str(target)], capture_output=True, text=True
        )
        self.assertEqual(run.returncode, 0, run.stderr)
        recovered = json.loads(run.stdout)
        self.assertEqual(len(recovered["records"]), 6)
        self.assertEqual(set(recovered["categories"]), {"legacy-archive"})
        archive = json.loads(self.out.read_text())
        actual = [x for x in recovered["records"] if x["kind"] == "legacy-archive-row"]
        for table in ("memories", "raw_captures", "schema_meta"):
            self.assertEqual(
                sorted(
                    [x["cells"] for x in actual if x["table"] == table], key=json.dumps
                ),
                sorted(archive["tables"][table]["rows"], key=json.dumps),
            )
            self.assertTrue(
                all(
                    x["columns"] == archive["tables"][table]["columns"]
                    for x in actual
                    if x["table"] == table
                )
            )
        original_target = target.read_bytes()
        with self.assertRaises(ValueError):
            m.import_archive(self.out, target, "legacy-archive/fictional")
        self.assertEqual(original_target, target.read_bytes())

    def test_stat_only_source_change_is_rejected(self):
        original = m.source_state
        calls = []

        def state(path):
            value = original(path)
            if Path(path) == self.source.resolve():
                calls.append(path)
                if len(calls) == 2:
                    # Simulate a detected concurrent change even if payload hashes match.
                    value["wal"]["stat"]["st_mtime_ns"] += 1
            return value

        with mock.patch.object(m, "source_state", side_effect=state):
            with self.assertRaisesRegex(ValueError, "changed"):
                m.export_archive(self.source, self.out)
        self.assertFalse(self.out.exists())

    def test_unknown_side_table_is_not_silently_lost(self):
        self.connection.execute("CREATE TABLE memories_fts_extra(private_note TEXT)")
        self.connection.execute(
            "INSERT INTO memories_fts_extra VALUES('Fictional extra evidence')"
        )
        self.connection.commit()
        before = bytes_of_source(self.source)
        with self.assertRaisesRegex(ValueError, "Unsupported schema objects"):
            m.export_archive(self.source, self.out)
        self.assertEqual(before, bytes_of_source(self.source))
        self.assertFalse(self.out.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
