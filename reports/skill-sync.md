# Skill sync report

- generated: 2026-09-27
- crawl4ai: 0.9.4 (skill expects 0.9.x: match)
- docs mirror: 48 pages, snapshot `083d26a85288`
- docs commit: `1f68e5bd` (2026-09-25) — unclecode/crawl4ai/develop
- baseline: git HEAD:docs/crawl4ai/_manifest.json
- result: in sync

## Upstream docs changes

### added (0)

None.

### changed (0)

None.

### removed (0)

None.

## Gates

- check_api.py: exit 0
  - crawl4ai: 0.9.4 (skill expects 0.9.x: match)
  - checked: {'imports': 68, 'params': 103, 'methods': 16, 'result_fields': 29, 'rejected_params': 4, 'defaults': 104}
  - drift: none (all referenced APIs present)
- .style_check.py: exit 0
  - SKILL.md                     lines= 131
  - evals/README.md              lines=  42
  - evals/run_trigger.py         lines= 167
  - references/API.md            lines= 185
  - references/PATTERNS.md       lines= 266
  - references/TROUBLESHOOTING.md lines=  62
  - scripts/check_api.py         lines= 408
  - issue count: 0

## Probes (live)

| claim | documented | observed |
| --- | --- | --- |
| example.com default crawl: raw_markdown length | 166 | 166 |
| example.com css_selector="main": raw_markdown length | 1 | 1 |
| news.ycombinator.com JsonCss tr.athing record count | 30 | 30 |

## Agent pass

- `opencode/muse-spark-1.3-contributor-free`: exit 0, 0 action(s) left — accepted

## Actions

- [ ] none
