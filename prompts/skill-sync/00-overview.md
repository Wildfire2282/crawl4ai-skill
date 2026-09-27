# Skill update prompt kit

Entry point for an agent asked to bring `.agents/skills/crawl4ai/` back in step with the upstream
docs mirror and the installed package. Stages run in order; each names the artefact it reads and the
command that proves it.

| Stage | Prompt | Proves itself with |
| --- | --- | --- |
| 1 triage | `01-triage.md` | a written plan, one line per upstream page |
| 2 references | `02-references.md` | `python .agents/skills/crawl4ai/scripts/check_api.py` |
| 3 SKILL.md | `03-skill-md.md` | `python .style_check.py` |
| 4 evidence | `04-evidence.md` | the markers in every claim the run touched |
| 5 verdict | `05-verify.md` | `python scripts/update_skill.py --check-only` |

Inputs:

- `reports/skill-sync.md` — this run's diagnosis: the upstream docs changes, the gate output, the actions left.
- `docs/crawl4ai/*.md` — the mirror, verbatim upstream Markdown with `source:`/`title:`/`fetched:` front matter.
- the installed `crawl4ai` package — import it; it is the source of truth for names, signatures and defaults.

Rules that fail the run when broken:

1. Never state an observed value that was not observed in this session.
2. Never edit `docs/crawl4ai/`, `docs/crawl4ai/_manifest.json`, `docs/crawl4ai/_INDEX.md` or `reports/skill-sync.md` — scripts own them.
3. Never hand-edit the bodies of the generated lists in `check_api.py` (`imports`, `run_params`, `browser_params`, `methods`, `result_fields`); cite the name in prose and let `update_skill.py` merge it.
4. Never delete, weaken or widen a check, a gate or a test to reach green. Fix the cause, or leave the action unresolved in the report.
5. `SKILL.md` front matter (`metadata:`, `compatibility:` and the `Targets crawl4ai X.Y.x` line) is script-owned.
6. Anything unresolved stays an action in the report: the next run has to see it, so an action is closed by fixing the cause, never by deleting the line that names it.
