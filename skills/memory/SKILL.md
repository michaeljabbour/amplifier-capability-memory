---
name: memory
description: "Keep scoped evidence and derived facts retrievable beyond one agent session. Use when asked to remember, retrieve, revise or inspect durable project evidence."
---

# Memory

Memory is a consumer of the separate amplifier-data storage capability. Keep that modular boundary: multiple capabilities may share the storage substrate, and this skill must not redefine or silently replace its AI-shaped contract.

Remember: retain task-relevant verbatim evidence with explicit wing/room scope and source/session/revision metadata when available. Do not capture incidental secrets or personal material merely because it appears in context. Automatic capture is an optional host integration, not a requirement of this method.

Retrieve: constrain searches to the relevant project and room. Return source passages and distinguish evidence from distilled facts and navigation indexes. A result recorded earlier is not an observation of current reality. Inspect the source before relying on a remembered claim whose currency matters.

Maintain: read references/reflection-rubric.md for evidence-to-fact distillation. Derived facts require provenance. Supersede stale facts without deleting the evidence trail. For an explicitly selected Project Memory SQLite schema-1 store, read references/legacy-archive.md and use its stdlib exporter/new-log archival import; other legacy formats remain unsupported. Export or migrate only through a documented adapter and explicit destination; never discover and convert an existing store as an installation side effect. The native log is append-only: invalidating a fact does not erase its bytes. For an authorized deletion request, inspect the actual retention/export procedure and identify separate backups; do not claim invalidation is physical deletion.

Read references/storage-boundary.md before runtime setup. Run scripts/runtime_doctor.py to inspect native availability without opening any user store. The portable method needs no database to install. Persistent execution requires a supported amplifier-data distribution. The narrow memory-evidence CLI uses the retained NativeMemoryStore directly without a model, daemon or host; full automated capture and briefing require the optional host adapter. Doctor must report an unavailable substrate honestly; it cannot make an unknown storage dependency disappear. Historical retrieval figures describe their original recorded protocol only, not this consolidation.

## Optional coaching checkpoint

Read [the local coaching guide](references/coaching-session.v1.md) only when the person asks for practice or optional session bookkeeping. Keep native operations direct and unattended; the guide adds only a separate opt-in pre/post review.
