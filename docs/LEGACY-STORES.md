# Existing stores and export boundaries

The portable Memory method installs independently. Its native execution backend uses the separately owned amplifier-data foundation. A clean public Data export is under owner review; the original private repository and history remain private. No old store is discovered, opened or converted by installing the method.

| Store | Existing format/location | Supported transition in this release |
|---|---|---|
| Project Memory bundle | SQLite at a project's `.amplifier/project-memory/memory.db`, with `memories`, `raw_captures` and `schema_meta` | No SQLite-to-native adapter is shipped. Keep the original database and source history. |
| Standalone tool-memory 0.1.x | SQLite, normally `~/.amplifier/memories.db`, with observations and session/file context | No full-fidelity adapter is shipped. The old module's memory export does not establish transfer of every related table. |
| Former vendor-backed Memory | The source and destination configured for that historical version | The former one-time importer and migration extra were removed. Historical release notes describe history, not a currently installed command. |
| Current native Memory | An explicitly selected amplifier-data append-only log | Preserve the original log for replay/regeneration. An evidence view is useful for inspection but cannot replace the log. |

Before any requested migration, identify the actual format, schema/version, configured path, writer processes, source revision and destination. Work on a consistent backup; a SQLite store in WAL mode can have uncheckpointed state outside its main file. Do not delete journals or copy only the main file while a writer is active. A future adapter must prove counts, exact content, identifiers, timestamps, explicit/observed provenance, unprocessed captures and scope mappings, with rejected or unmapped fields reported. It must preserve the source and provide rollback. These are acceptance requirements, not a claim that such an adapter exists.

Do not use the old Project Memory `MemoryStore` constructor as a supposedly read-only reader: it initializes schema and WAL mode, and some read methods update access counters. A reviewed exporter would need an explicit read-only SQLite connection against a consistent copy. No user store was opened while preparing this release guidance.

The supported `memory-evidence --store PATH export --wing WING [--room ROOM]` emits `memory-evidence-view/1`. It returns at most 10,000 drawers within the selected scope. It is not a full-fidelity native log backup, a complete graph/event export, a legacy SQLite reader, or proof that all data was transferred. Keep the source log and verify any destination separately. Search/export use `record_access=False`; that alone is not an immutable-storage or physical-deletion guarantee.

Do not retire old storage code merely because the new method is published. Retirement requires the Data distribution decision, an independently installable native path, an identified consumer/store inventory, a tested applicable export/import path and an owner-reviewed rollback. Existing data and historical implementations remain available until those gates are met.
