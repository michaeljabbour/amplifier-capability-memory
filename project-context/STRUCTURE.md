# Public source layout

- `modules/tool-memory/`: native Memory tool, standalone evidence CLI and its module-level tests.
- `modules/*/tests/`: direct module contract/unit tests; optional host and model dependencies have their own acceptance requirements.
- `skills/memory/`: portable method and its self-contained references.
- `docs/NATIVE-QUICKSTART.md`: explicit no-model evidence path; `README.md` separates it from optional host automation.
- `project-context/`: retained coordination and historical evidence. Historical test totals do not certify the current source.

The 2026-11-02 review adds `modules/tool-memory/tests/test_evidence_cli_scope.py`; it checks preflight behavior without opening a real log.
