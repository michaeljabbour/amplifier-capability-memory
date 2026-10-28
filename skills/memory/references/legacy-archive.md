# Project Memory schema-1 archival bridge

Use only for an explicitly selected Project Memory SQLite schema-1 store and a new output. Do not discover a store or convert it during installation. The standalone observation/session SQLite schema and former vendor store are not supported by this bridge.

1. Quiesce writers/readers and retain a consistent original backup, including WAL state. The source is evidence; do not instantiate the old MemoryStore to read it.
2. Export with the stdlib helper from this installed skill directory:

```text
python3 scripts/legacy_sqlite_archive.py export EXPLICIT_SOURCE.db --out NEW_ARCHIVE.json
```

The exporter hashes/stats the original DB/WAL/SHM, copies DB/WAL bytes into a temporary directory, opens only that snapshot via SQLite `mode=ro`, reads all three source tables in a transaction, and verifies the original fingerprints again. It rejects detected changes, unsupported versions, missing/unknown columns, extra unknown tables and existing destinations. It does not lock out concurrent writers; changed or larger stores need a separately reviewed consistent-snapshot workflow.

`project-memory-archive/1` preserves every column and row in `memories`, `raw_captures`, and `schema_meta`, including source primary keys, raw captures, metadata, timestamps and SQLite null/blob/text/integer/real types. Source schema metadata and fingerprints are retained. There is no row limit; the DB/WAL/SHM input cap is 64 MB and artifact cap 128 MB. Over-limit cases fail without a partial artifact. This archive excludes derived FTS/indexes and SQLite internals; it is not a complete database-file backup. An editable artifact is not a cryptographically authenticated provenance claim.

3. If native Memory and the separately owned Data foundation are installed, explicitly import into a **new** log:

```text
python3 scripts/legacy_sqlite_archive.py import NEW_ARCHIVE.json --new-store NEW_NATIVE.log --wing legacy-archive/FICTIONAL_PROJECT
```

The scope label is illustrative. Select the intended archive scope. Existing destinations are refused. The importer uses the real NativeMemoryStore/Data APIs; it does not add or substitute a storage backend. It stores a manifest and opaque typed source rows with archival category/provenance, disables semantic passage derivation for this transfer, checks payload bytes after reopening the native log, and publishes the new log exclusively only after verification. The receipt identifies source row counts, artifact/log hashes and the archival scope.

4. Review the archive and receipt before making any separate adoption decision. Imported source categories/importance remain data inside each source row; they do not become current adopted facts. Do not enable briefing over the archive without reviewing its semantics. The bridge does not reproduce old decay, deletion, FTS ranking or hook behavior. Retain source database and code for rollback. No real user store has been migrated by the release checks.

The native import path remains unavailable to outside users until they have an authorized Data distribution. The portable exporter itself requires no Memory/Data package, model, credential, host hook or network.
