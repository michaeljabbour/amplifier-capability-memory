# Separate storage owner and explicit native runtime

The separate amplifier-data library owns Cells, append-only logs, regeneration and swappable lenses. Memory remains a consumer. Its source is private; it must not be made public as a side effect of publishing this skill.

With authorized sibling checkouts, build/install amplifier-data first (`python3 -m pip install ../amplifier-data`). Rust is required for durable paths. For the narrow no-embedding evidence CLI, `python3 -m pip install --no-deps ./modules/tool-memory` deliberately uses that installed local foundation and omits the optional embedding runtime. This mode needs no model, host or daemon. Run `amplifier-data-doctor --self-test` and the native evidence acceptance check before using it. The full existing daemon/hooks path still uses its declared pinned foundation, fastembed and NumPy requirements.

`memory-evidence --store NEW_LOG remember --wing fictional-project --room decisions --content "Fictional evidence"` writes through the retained NativeMemoryStore into amplifier-data. Search is lexical/BM25 when no embedding vector is supplied. `export` emits a bounded human-readable evidence view, not a complete lossless backup. Preserve the original native log for regeneration and native metadata; use one writer or the companion server for multi-process access. Installation never discovers, migrates or rewrites existing user data.

A persistent source-access failure is a release boundary. It must remain visible in doctor and distribution documentation; a replacement SQLite store is not shipped to conceal it.
