# Stage 1 — triage

Read `reports/skill-sync.md`. Work the "Upstream docs changes" section one page at a time, and decide
before editing anything.

- `added` — decide, and name the consequence:
  - belongs in the skill → the file and section that carries it (a `Routing` row in `SKILL.md`, a
    recipe in `references/PATTERNS.md`, an entry in `references/API.md`);
  - belongs in the mirror's policy → the reason string, in the style the existing entries use, for
    `SECTIONS`, `CURATED_OUT` or `SITE_PAGE_REASONS` in `scripts/sync_docs_repo.py`;
  - needs nothing → why (site page, release notes, duplicate of a page already carried).
- `changed` — the report names either the skill files that cite the page (`cited by`) or the closest
  section (`overlap`). Re-read the mirrored file, then answer concretely: which sentence in those
  files is now wrong, and what should it say instead? Quote the sentence.
- `removed` — find what depended on it and re-point that text, or delete it.

Also read the report's "Upstream pages not carried" section: it lists sections or root pages upstream
started offering that the mirror's policy leaves out. Carry one by adding its section to `SECTIONS`, or
record why it stays out, in the same file. A new page inside a section the policy already excludes
needs no decision.

Output: a plan, one line per page — `page → file:section → what changes`. No edits in this stage.
Every upstream page appears in the plan, including the ones judged to need nothing, with its reason.
