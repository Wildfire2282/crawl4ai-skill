# Stage 3 — SKILL.md

`SKILL.md` is the routing layer: preflight, `Routing`, `Procedure`, `Reference implementation`,
`Expected outputs`, `Invariants and failure modes`, `Files`. Change it only where stage 1's plan says
routing moved.

- New capability → one `Routing` row (`Condition | API | PATTERNS.md §`) plus the recipe it points at,
  and the recipe count in the prose kept equal to the recipes that exist.
- Changed default or behaviour → the `Invariants and failure modes` row, the `Expected outputs` row and
  any example that shows the old value, updated together.
- Removed capability → delete the row and the text it pointed at; a row pointing at deleted text is
  worse than a gap.
- Preflight stays short: it answers "which gate failed, what to do", nothing else.

Leave the `Notation` block and the front matter alone. A marker kind that this run introduces is the
one exception: it is registered in `Notation` in stage 4.
