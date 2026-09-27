# Stage 4 — evidence markers

Every claim about observed behaviour carries the marker its evidence earns. The kinds are the ones
`Notation` in `SKILL.md` lists; do not invent a new one without registering it there in this pass.

| Marker | Means | Earned when |
| --- | --- | --- |
| `[verified: run]` | output quoted from a crawl executed in this session | the command ran here and its output was read |
| `[verified: construct]` | imports and object construction checked | the object was imported and built, nothing more |
| `[verified: source]` | read from the installed package's source or introspection | the file, signature or attribute was opened |
| unmarked | API-level fact from introspected signatures | the signature was inspected |

- Never upgrade a source reading to `[verified: run]` because the two "must" agree.
- A value that drifts between runs (page content or length, live record counts, cache timing,
  telemetry) states the session it was observed in.
- A quoted value that changed since the last observation is replaced, date included; the old value is
  not kept beside it.
- A quoted output with no marker is a defect: run it, or mark it for what it is.
- The version in the notation line stays the version that was actually installed during the pass.
