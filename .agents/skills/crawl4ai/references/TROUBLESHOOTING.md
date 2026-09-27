# Crawl4AI troubleshooting

Purpose: symptom-to-fix lookup for completed runs with wrong or empty output.
Verification: `[verified: run]` = reproduced against crawl4ai 0.9.4 on 2026-09-27; unmarked causes are parameter-level failures implied by the introspected signatures.

## A. Markdown empty or incomplete

| Symptom | Cause | Fix | Detection |
| --- | --- | --- | --- |
| `success=True`, `status_code=200`, `raw_markdown` ≈1 char on a page known to contain content | `css_selector` matched nothing (the element is absent, or the DOM differs after JS execution) `[verified: run]` | Remove the selector, or target an element verified in `result.html`; re-check after `wait_for` | `cleaned_html` collapses with the selector present (283 → 13 chars on `https://example.com` with `css_selector="main"`) |
| `raw_markdown` empty or single heading | `word_count_threshold` pruned the blocks; or the content renders client-side | Lower `word_count_threshold`; add `wait_for="css:<visible element>"` or `js_code` | Compare `len(result.html)` with `len(result.markdown.raw_markdown)` |
| Navigation, footer and banners present in Markdown | No content selector, whole page converted `[verified: run]` | `css_selector="main"` (or `"article"`, `"#content"`); add `excluded_tags=["nav","footer"]`, `remove_overlay_elements=True`, `remove_consent_popups=True` | `Brand Book`-style nav strings present in output |
| Current page content expected, previous version returned | A copy was written and reused under `cache_mode=CacheMode.ENABLED` (or `READ_ONLY`); the 0.9.4 `CrawlerRunConfig()` default is `CacheMode.BYPASS` and reports `cache_status="miss"` on every run `[verified: run]` | `cache_mode=CacheMode.BYPASS` during development; `check_cache_freshness=True` where the reuse is intentional (§14 of `PATTERNS.md`) | `result.cache_status` is `"hit"` or `"hit_validated"`; `result.cached_at` predates the run |
| `result.markdown.fit_markdown` empty | No content filter configured `[verified: run]` | `DefaultMarkdownGenerator(content_filter=PruningContentFilterLXML(...))` (0.9.4 deprecates the BeautifulSoup-based `PruningContentFilter`) or `BM25ContentFilter(user_query=...)` | `len(fit_markdown) == 0` with `raw_markdown` populated |

## B. `result.success` is `False`

| `error_message` / status | Cause | Fix |
| --- | --- | --- |
| Browser executable missing | Playwright browsers not installed | `crawl4ai-setup`; verify `crawl4ai-doctor` |
| Timeout | Readiness condition never satisfied | Raise `page_timeout`; replace fixed delays with `wait_for` / `wait_until`; confirm the host is reachable from this network |
| 403 / 429 / challenge page | Bot defense | `enable_stealth=True`, `UndetectedAdapter` on the crawler strategy, `ProxyConfig` with residential egress, `RateLimiter`, lower `max_session_permit` |
| TLS verification error | Untrusted or self-signed chain | `ignore_https_errors=True` when the origin is trusted; otherwise fix the chain |
| Connection reset under concurrency | Too many parallel browser sessions | `MemoryAdaptiveDispatcher(max_session_permit=<lower>)`; watch `critical_threshold_percent` |
| `robots.txt` disallowed | `check_robots_txt` enabled for this target | Confirm authorization before disabling; the flag exists on `CrawlerRunConfig` |

`result.success` is `False` with an empty `raw_markdown`; unguarded consumption of `result.markdown.raw_markdown` therefore emits empty output instead of failing.

## C. Extraction

| Symptom | Cause | Fix | Detection |
| --- | --- | --- | --- |
| `extracted_content is None` | No `extraction_strategy` set on the run config | Assign the strategy to `CrawlerRunConfig` | `result.extracted_content` |
| `json.loads(...) == []` with a valid-looking schema | `baseSelector` matches nodes that cleaning removed from `cleaned_html`; whether chrome survives is site-dependent `[verified: run]` | Target content nodes; add `css_selector` for the content region | Count matches in `result.cleaned_html` before trusting the schema |
| `None` field values inside valid records | Field `selector` is relative to `baseSelector` and did not match | Validate the selector pair against `result.cleaned_html`; use `type: "attribute"` with `attribute: "href"` for attributes | Per-field `None` count |
| LLM extraction returns prose | `instruction` or `schema` absent; model ignored the format | Supply `instruction` and `schema`; set `force_json_response=True`; use a stronger model | Response is not parseable JSON |
| LLM extraction fails immediately | Missing or invalid `api_token`, unknown `provider` | `LLMConfig(provider=..., api_token=os.environ[...])` | Exception text from the provider client |
| Values missing from long pages | Content exceeded the chunk budget | Tune `chunk_token_threshold`, `overlap_rate`, `apply_chunking` | Record count below expectation on long inputs |

## D. Scale, traversal and process

| Symptom | Cause | Fix |
| --- | --- | --- |
| `arun_many` return shape differs between call sites | `stream=True` yields an async generator; without it the awaited result is an iterable container `[verified: construct]` | Normalise at one call site; keep consumers shape-agnostic |
| Deep crawl does not terminate | `max_pages` unset; traversal unbounded | Set `max_pages`, add `FilterChain`, set `score_threshold` |
| Same URLs crawled repeatedly | Tracking or query-string variants | `URLPatternFilter(reverse=True)` for noise patterns; `ContentTypeFilter` to skip binaries |
| Host memory exhausted on large batches | Dispatcher ceiling above the host limit | Lower `memory_threshold_percent` and `critical_threshold_percent`; reduce `max_session_permit` |
| `RuntimeError: asyncio.run() cannot be called from a running event loop` | Synchronous call inside an async application or notebook | `await crawler.arun(...)`; in notebooks use top-level `await` |
| `Event loop is closed`, browser unusable after first run | One `AsyncWebCrawler` instance reused across separate `asyncio.run()` calls | Construct and close the crawler inside the loop in use |
| Authentication holds for the first page only | Session not propagated | Reuse `session_id` in every run config; confirm `result.session_id`; in CLI runs pass `-c "session_id=..."` |
| Downloaded files absent | Download support not enabled | `BrowserConfig(accept_downloads=True, downloads_path=...)`; read `result.downloaded_files` |
| PDF URL returns an HTML viewer | The URL hosts a viewer rather than the file | `CrawlerRunConfig(pdf=True)` for embedded PDFs; `PDFContentScrapingStrategy` for direct PDF URLs |

## E. Skill and installed version diverge

```bash
python scripts/check_api.py [--json]
```

Exit 0 = all referenced APIs present; `--json` emits the report as JSON.

Exit 1 lists each missing name, parameter or field. On exit 1, the installed package overrides this skill: re-derive the affected call from `inspect.signature(...)` and report the drift instead of adapting silently.
