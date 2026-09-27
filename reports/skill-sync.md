# Skill sync report

- generated: 2026-09-27
- crawl4ai: 0.9.4 (skill expects 0.9.x: match)
- docs mirror: 48 pages, snapshot `da1a2a66c390`
- baseline: none (git has no committed manifest yet)
- result: in sync

## Upstream docs changes

No committed baseline to diff against: this run only records the current snapshot.

## Gates

- check_api.py: exit 0
  - crawl4ai: 0.9.4 (skill expects 0.9.x: match)
  - checked: {'imports': 68, 'params': 103, 'methods': 16, 'result_fields': 29, 'rejected_params': 4, 'defaults': 104}
  - drift: none (all referenced APIs present)
- .style_check.py: exit 0
  - evals/README.md              lines=  42
  - evals/run_trigger.py         lines= 167
  - references/API.md            lines= 185
  - references/PATTERNS.md       lines= 266
  - references/TROUBLESHOOTING.md lines=  62
  - scripts/check_api.py         lines= 408
  - SKILL.md                     lines= 130
  - issue count: 0

## Probes (live)

| claim | documented | observed |
| --- | --- | --- |
| example.com default crawl: raw_markdown length | 166 | 166 |
| example.com css_selector="main": raw_markdown length | 1 | 1 |
| news.ycombinator.com JsonCss tr.athing record count | 30 | 30 |

## Actions

- [ ] none
