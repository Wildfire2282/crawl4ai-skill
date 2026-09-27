---
name: crawl4ai
description: Use this skill for any task that collects data from websites with Crawl4AI — page to Markdown conversion, structured record extraction via CSS/XPath schemas or an LLM, multi-page and whole-site crawls, and the handling of JS-rendered content, authentication, proxies, bot defenses, PDFs and large batches. Covers authoring, reviewing and debugging crawl code (AsyncWebCrawler.arun, arun_many, BrowserConfig, CrawlerRunConfig, CacheMode, dispatchers, deep-crawl strategies), selecting extraction strategies, and diagnosing empty or malformed output — including requests that only say scrape, crawl, harvest, monitor or extract site data without naming Crawl4AI.
license: Apache-2.0
compatibility: Requires Python 3.10+, the crawl4ai package, Playwright browsers (crawl4ai-setup) and network access at run time. Targets crawl4ai 0.9.x.
metadata:
  upstream: https://docs.crawl4ai.com
  api-tracked: 0.9.4
  verified: "2026-09-27"
  docs-snapshot: d179c20858e8ef55
  docs-pages: 48
  docs-synced: 2026-09-27
---

# Crawl4AI

Scope: Crawl4AI usage — configuration, extraction, crawling strategies, failure diagnosis.

Paths in this skill are relative to this skill's directory (the parent of this file).

Notation:
- `[verified: run]` — executed against crawl4ai 0.9.4 on 2026-09-27; observed output quoted.
- `[verified: construct]` — imports and object construction checked against crawl4ai 0.9.4; not executed end to end.
- `[verified: source]` — read from the installed crawl4ai 0.9.4 source; nothing executed.
- Unmarked statements are API-level facts derived from introspected signatures.

## Preflight

Run before writing any crawl code. Stop at the first failing gate.

```bash
python scripts/check_api.py                     # gate: requested APIs exist in the installed package
python -c "import importlib.metadata as m; print(m.version('crawl4ai'))"
crawl4ai-doctor
```

| Gate failure | Action |
| --- | --- |
| `check_api.py` exits 1 | The installed version drifts from this skill. Use the installed package as source of truth: `python -c "import inspect, crawl4ai; print(inspect.signature(crawl4ai.CrawlerRunConfig))"`; report the drift. |
| `crawl4ai` not importable | `pip install crawl4ai` |
| `crawl4ai-doctor` reports missing browsers | `crawl4ai-setup` |

## Routing

Select one row. Open only the referenced section.

| Condition | API | `PATTERNS.md` § |
| --- | --- | --- |
| Single known URL to Markdown | `AsyncWebCrawler.arun()` | §1 |
| Known URL list | `arun_many(urls, dispatcher=MemoryAdaptiveDispatcher(...))` | §2 |
| Unknown URL set on one site | `deep_crawl_strategy=BFSDeepCrawlStrategy(...)`, `FilterChain` | §3 |
| Adaptive crawl until a query is covered | `AdaptiveCrawler`, `AdaptiveConfig` | §4 |
| Re-fetch only pages that changed since the last run | `cache_mode=CacheMode.ENABLED` + `check_cache_freshness`, `result.cache_status` | §14 |
| URL discovery without crawling | `AsyncUrlSeeder`, `DomainMapper` | §5 |
| Authenticated or stateful session | `session_id`, `BrowserConfig.cookies`, crawler-strategy hooks | §6 |
| Content present only after JS execution or scrolling | `wait_for`, `js_code`, `scan_full_page`, `VirtualScrollConfig` | §7 |
| Structured records, stable markup | `JsonCssExtractionStrategy`, `JsonXPathExtractionStrategy`, `RegexExtractionStrategy` | §8 |
| Structured records, unstable or semantic markup | `LLMExtractionStrategy`, `LLMConfig` | §9 |
| Chunks for retrieval or filtered text | content filters, chunking strategies | §10 |
| Table data | `DefaultTableExtraction`, `LLMTableExtraction` | §11 |
| Proxies, stealth, TLS bypass, PDFs, screenshots | `ProxyConfig`, `RoundRobinProxyStrategy`, `UndetectedAdapter`, `pdf=True` | §12 |
| Shell execution requested | `crwl crawl <url>` | §13 |

Default configuration: `BrowserConfig(headless=True)` + `CrawlerRunConfig()`, whose `cache_mode` already defaults to `CacheMode.BYPASS` in 0.9.4 — upstream prose still claims `ENABLED`. Modify one parameter per iteration.

## Procedure

Execute in order. Each checkbox is a gate: do not proceed past a failed step.

- [ ] **1. Verify the environment** (Preflight). Rationale: a drifted API or missing browser produces failures that look like site problems.
- [ ] **2. Probe the target once** with default configuration. Record `result.success`, `result.status_code`, `len(result.html)`, `len(result.cleaned_html)`, `len(result.markdown.raw_markdown)`. Classify before configuring: transport failure (status/error), render failure (`html` populated, `cleaned_html` empty), or configuration failure (content in `cleaned_html`, absent from Markdown). Rationale: these three classes have disjoint fixes, and one probe distinguishes them cheaply.
- [ ] **3. Route the task** (Routing) and open the referenced section only.
- [ ] **4. Author the crawl** with explicit `cache_mode`, a `result.success` branch, a content selector only when the target page is known to contain that element, and an extraction strategy when fields are required.
- [ ] **5. Execute and inspect output**: record count, Markdown length, or `result.error_message`. Rationale: code that compiles and a crawl that reports `success=True` are both compatible with an empty result.
- [ ] **6. Diagnose before adjusting** any parameter: locate the symptom in `references/TROUBLESHOOTING.md`. Rationale: parameter changes made without a diagnosis destroy the evidence of the original failure.

Deliverable: a script printing Markdown or JSON for one-off tasks; a function taking URLs and a `CrawlerRunConfig` and returning `CrawlResult`s for recurring tasks, with concurrency and cache policy explicit.

## Reference implementation

```python
import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

async def main():
    async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as crawler:
        result = await crawler.arun(
            "https://example.com",
            config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS),
        )
        if not result.success:
            raise RuntimeError(result.error_message)
        print(result.markdown.raw_markdown)

asyncio.run(main())
```

`[verified: run]` `https://example.com`: `success=True`, `status_code=200`, `len(result.markdown.raw_markdown)=166`. Add `css_selector="main"` only after confirming the target page contains that container; see the `css_selector` invariant below.

## Expected outputs

| Input | Configuration | Observed output | Status |
| --- | --- | --- | --- |
| `https://example.com` | defaults, `CacheMode.BYPASS` | `success=True`, `status_code=200`, Markdown 166 chars, first line `# Example Domain` | `[verified: run]` |
| `https://news.ycombinator.com` | `JsonCssExtractionStrategy`, `baseSelector="tr.athing"`, fields `title` (text) and `url` (attribute `href`) | 30 records on 2026-09-27; record 0 `{"title": "\"They had no concept of a duty of care to their users.\"", "url": "https://unsung.aresluna.org/they-had-no-concept-of-a-duty-of-care-to-their-users/"}` — the headline on record 0 changes between runs, so only the record shape is stable | `[verified: run]` |
| `["https://example.com", "https://example.org"]` | `arun_many` + `MemoryAdaptiveDispatcher(max_session_permit=3)` | both `success=True`, both `status_code=200`, Markdown 166 chars each | `[verified: run]` |

## Invariants and failure modes

| Invariant | Violation consequence | Control |
| --- | --- | --- |
| A crawl result is inspected through `result.success` | Failed crawl yields empty Markdown without an exception | Branch on `result.success` before consuming output |
| `css_selector` matches an existing element | A non-matching selector returns `success=True`, `status_code=200` and a 1-char `raw_markdown`; `cleaned_html` collapses from 283 to 13 chars on `https://example.com` with `css_selector="main"` `[verified: run]` | Confirm the container exists in `result.html` before setting the selector; assert a minimum `len(raw_markdown)` |
| Cache reads reflect the current page version during development | `CacheMode.ENABLED` serves a previously written copy as current until it is validated or bypassed: second run of `https://example.com` under `CacheMode.ENABLED` reports `cache_status="hit"` with `cached_at` set, while the `CrawlerRunConfig()` default (`BYPASS`) reports `cache_status="miss"` on every run `[verified: run]` | `cache_mode=CacheMode.BYPASS`; `check_cache_freshness=True` when the reuse is intentional (§14) |
| Extraction selectors match content nodes | Chrome removal is site-dependent: extraction runs on `cleaned_html`, which may still carry navigation or sidebar markup — on `https://news.ycombinator.com` the nav survives and `baseSelector="span.pagetop"` returns 2 records instead of `[]`, without error `[verified: run]` | Validate selectors against `result.cleaned_html` before trusting a schema |
| `fit_markdown` has a filter source | `result.markdown.fit_markdown` is empty | `DefaultMarkdownGenerator(content_filter=PruningContentFilterLXML(...))`; 0.9.4 deprecates `PruningContentFilter` in favour of it |
| Helper code handles both `arun_many` return shapes | Awaited result is an iterable container on 0.9.4; `stream=True` yields an async generator `[verified: construct]` | Normalise once at the call site |
| Deep crawls are bounded | Unbounded traversal on `max_pages` unset | Set `max_pages` and a `FilterChain` |
| Playwright browsers are installed | `browser_type` without a matching install fails at run time | `crawl4ai-setup`; verify with `crawl4ai-doctor` |
| One event loop spans the crawler lifetime | Crawler reuse across separate `asyncio.run()` calls fails; `asyncio.run()` inside a running loop raises | Create and close the crawler inside the loop in use |

## Files

| File | Contents | Load trigger |
| --- | --- | --- |
| `references/PATTERNS.md` | 14 task recipes: configuration objects plus observed result shape | A Routing row was selected and code is required |
| `references/API.md` | Signatures, parameters, defaults, result fields, import paths, CLI flags | A parameter name, default, or import path is required |
| `references/TROUBLESHOOTING.md` | Symptom → cause → fix → detection tables | A run completes with wrong or empty output |
| `scripts/check_api.py` | Drift gate for every API, parameter, result field and documented default this skill references; the `generated:` list regions are refreshed by `scripts/update_skill.py` in the project root | Preflight, and after any crawl4ai upgrade |
| `evals/` | Output test cases (`evals.json`), output grader (`grade.py`), trigger queries (`trigger_queries.json`), trigger runner (`run_trigger.py`), usage notes (`README.md`) | Only when editing or evaluating this skill; never during a crawl task |
