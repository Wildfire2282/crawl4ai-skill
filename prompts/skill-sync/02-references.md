# Stage 2 — references

Apply the plan to `.agents/skills/crawl4ai/references/`. Read each mirrored page before writing about
it, and take every name, parameter and default from the installed package.

`API.md` — entry points and signatures, grouped as the file already groups them.

- Inspect what is being documented: `python -c "import inspect, crawl4ai; print(inspect.signature(crawl4ai.CrawlerRunConfig))"`,
  the same for `BrowserConfig`, `CrawlResult.model_fields`, dispatchers and strategies.
- A default watched by the gate (`DEFAULTS` in `check_api.py`) has to match the installed package. If
  the package moved it, the reference that states the old value and the `DEFAULTS` entry change in the
  same pass — the gate stays red until both agree.

`PATTERNS.md` — numbered recipes, each with intent → code → observed result.

- A recipe whose behaviour changed is re-read against its mirrored page. If it runs cheaply in this
  session, run it and quote the output with the marker; if it cannot run, say so in the recipe.
- A new capability from the plan becomes a new recipe in the same shape, and the `Routing` table gets
  the row that points at it.

`TROUBLESHOOTING.md` — lettered sections, symptom → cause → fix → detection.

- A failure mode observed in this session is added; a fix that no longer applies is deleted rather
  than kept as history.

Keep the register the files already use: tables for facts that are tabular, no pronouns, no filler.
