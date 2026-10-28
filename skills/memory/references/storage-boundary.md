# Separate storage owner and explicit native runtime

The independent [Amplifier Data library](https://github.com/michaeljabbour/amplifier-tool-data) owns Cells, append-only logs, regeneration and swappable lenses. Memory remains a one-way consumer. The original private Data repository/history stays private; the reviewed code-only public distribution supplies the native dependency.

For an anonymous source install, use `python3 -m pip install 'git+https://github.com/michaeljabbour/amplifier-tool-data@40450647367db2a2b5058bea1d81a6d248c24c94'`. Python 3.11+, Rust and a native compiler are needed. Then install Memory's module with `python3 -m pip install --no-deps 'git+https://github.com/michaeljabbour/amplifier-skill-memory@main#subdirectory=modules/tool-memory'`. This narrow evidence route deliberately omits the embedding runtime; the full daemon/hooks path still uses its declared fastembed and NumPy requirements.

Run `amplifier-data-doctor --self-test` and this package's runtime doctor. Native durability must be true. `memory-evidence --store NEW_LOG remember --wing fictional-project --room decisions --content "Fictional evidence"` writes through the retained NativeMemoryStore without a model, daemon or host. Search is lexical/BM25 without an embedding vector. `export` is a bounded human-readable evidence view, not a complete lossless backup.

Preserve the native log for regeneration and metadata. Use one writer or the companion server for multiple processes. Installation never discovers, migrates or rewrites existing user data. Doctor reports missing or non-native Data honestly; no replacement backend is shipped to conceal an unavailable dependency.
