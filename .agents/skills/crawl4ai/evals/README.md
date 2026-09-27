# Evaluations

Purpose: measure this skill's activation and output quality. Not loaded during crawl tasks.

| File | Contents |
| --- | --- |
| `evals.json` | Output test cases: prompt, expected output, mechanical assertions |
| `trigger_queries.json` | Trigger queries with `should_trigger` labels and a train/validation split |
| `run_trigger.py` | Runs the trigger set against an agent CLI and applies the trigger-rate threshold |
| `grade.py` | Grades the `evals.json` assertions against a directory of produced output |

## Trigger evaluation

```bash
python evals/run_trigger.py --runs 3                 # full set, 3 runs per query
python evals/run_trigger.py --runs 3 --split train   # iterate on this; keep validation unseen
python evals/run_trigger.py --json                   # machine-readable results
```

Trigger detection is mechanical: a run counts as triggered when the agent reads this skill's body, or when its final message contains a Crawl4AI-specific API identifier (`AsyncWebCrawler`, `CrawlerRunConfig`, `JsonCssExtractionStrategy`, `CacheMode`, `crwl`, ...). A query with `should_trigger: true` passes at a trigger rate ≥ 0.5; `false` passes below 0.5.

Run each query from a clean context. Queries must not be edited to match observed results; add new queries and keep the split fixed so iterations stay comparable.

## Output evaluation

Per `evals.json`, each case runs twice — with the skill and without it — into separate run directories:

```
<run-dir>/with_skill/      # whatever the eval prompt produced; grade.py reads out/ when present
<run-dir>/without_skill/
```

Grade a run directory with the shipped grader:

```bash
python evals/grade.py <run-dir>/with_skill            # text report with per-assertion evidence
python evals/grade.py <run-dir>/with_skill --json     # machine-readable report
```

Exit 0 = every assertion passed, 1 = at least one failed, 2 = invalid input. The grader resolves `evals.json` beside itself, so it runs from any working directory.

Assertions are file-level and mechanical (file exists, size bound, string present, JSON parses, element count, field shape). They were calibrated on three run directories — real output (`8/8`), empty output (`0/8`) and malformed output (`2/8`, the two that only require files to exist) — so they discriminate rather than pass unconditionally. The calibration runs are kept at the repository level under `.evalcheck/run/`.
