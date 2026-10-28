# Save a note and find it in a fresh process

Use this when you want an explicit, inspectable local record of project evidence. This quickstart saves verbatim text in a new log and searches it with lexical/BM25 matching. It does not start a daemon or download an embedding model.

## What you need

Python 3.11+ and Git. Durable storage is built by the separately released Data library, so a Rust toolchain (`cargo` and `rustc`) and a native compiler are required for this source install. The reviewed prebuilt Data wheel is available for macOS Apple silicon; other platforms need a source build and their native acceptance remains unverified.

Start in an empty directory. These commands create a new virtual environment and a new fictional test log in that directory.

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install 'git+https://github.com/michaeljabbour/amplifier-tool-data@40450647367db2a2b5058bea1d81a6d248c24c94'
python3 -m pip install --no-deps 'git+https://github.com/michaeljabbour/amplifier-skill-memory@main#subdirectory=modules/tool-memory'
amplifier-data-doctor --self-test
memory-evidence --store ./fictional-quickstart.log remember --wing fictional-project --room decisions --content 'Fictional parser check remains unverified.' --source fictional-note
memory-evidence --store ./fictional-quickstart.log search --wing fictional-project --query parser
```

The doctor must report `rust_extension: true`, `durable_available: true` and `self_test.durable_restart: true`. Remember returns a content reference; the fresh search process returns the fictional note. The source and wing/room scope travel with the record. Close the terminal, activate the same environment and repeat the search to check the durable log yourself.

`--no-deps` above is deliberate: the evidence CLI uses the already installed Data package and no embedder or host. For the full Amplifier adapter, omit `--no-deps` when installing the module so its declared fastembed and NumPy dependencies resolve. Embedding models and automatic hooks require their own setup and acceptance; the small CLI check does not establish that path.

## Keep the right thing

The native log is the replayable source. `memory-evidence --store ./fictional-quickstart.log export --wing fictional-project` emits a bounded evidence view (up to 10,000 drawers), not a full log backup. Keep the original log. Use one writer per file, or the supported companion server for multiple processes. Invalidating a fact does not erase its bytes from an append-only log.

Remove the fictional log and `.venv` when finished. Never point an example at an existing store. For a real legacy store, first read [the supported formats and copy-only archive bridge](LEGACY-STORES.md); migration is a separate explicit operation.

## What has been checked

The public Data wheel and source resolve anonymously. A clean installed native Memory/Data pair was checked with two scoped consumers, exact Cell regeneration, separate-process evidence search and durable close/reopen. Tests use temporary fictional data. This is functional acceptance for the narrow native evidence path; it does not establish better answers, universal host support or a production migration.
