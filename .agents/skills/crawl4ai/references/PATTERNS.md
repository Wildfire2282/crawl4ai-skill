# Crawl4AI recipes

Purpose: the configuration objects each task requires, with the observed result shape.
Verification: `[verified: run]` = executed against crawl4ai 0.9.4 on 2026-09-27, live output quoted; `[verified: construct]` = imports and object construction checked only. Unmarked statements are API-level facts from introspected signatures.

Preamble: every recipe replaces the body of `main()` in the reference implementation in `SKILL.md` (imports, crawler construction and `asyncio.run` are defined there). Recipe variables are `crawler`, `config`, `result`.

## 1. Single page to Markdown

```python
config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
result = await crawler.arun("https://example.com", config=config)
print(result.markdown.raw_markdown)
```

Result: `[verified: run]` `success=True`, `status_code=200`, `len(result.markdown.raw_markdown)=166`.

Add `css_selector="main"` (or `"article"`, `"#content"`) when the page has a content container; otherwise site navigation enters the Markdown. A selector that matches nothing returns `success=True` with a 1-char Markdown `[verified: run]` — confirm the element exists in `result.html` first. Read `result.cleaned_html` when the Markdown is shorter than the page content.

## 2. Known URL list

```python
from crawl4ai import MemoryAdaptiveDispatcher, RateLimiter, CrawlerMonitor

dispatcher = MemoryAdaptiveDispatcher(
    max_session_permit=6,
    memory_threshold_percent=90.0,
    memory_wait_timeout=600.0,
    rate_limiter=RateLimiter(base_delay=(1.0, 3.0), max_retries=3),
    monitor=CrawlerMonitor(urls_total=len(urls), enable_ui=False),
)
outcome = await crawler.arun_many(urls, config=config, dispatcher=dispatcher)
for result in outcome:                      # awaited result is an iterable container on 0.9.4
    print(result.url, result.success, result.status_code)
```

Result: `[verified: run]` two URLs through `MemoryAdaptiveDispatcher(max_session_permit=3)`: both `success=True`, `status_code=200`, 166 chars each.

Alternatives: `SemaphoreDispatcher(semaphore_count=5)` for fixed concurrency; `stream=True` on the call to consume results as an async generator (normalise the return shape at one call site).

## 3. Bounded deep crawl

```python
from crawl4ai.deep_crawling import BestFirstCrawlingStrategy
from crawl4ai.deep_crawling.filters import FilterChain, URLPatternFilter, DomainFilter, ContentTypeFilter
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer, CompositeScorer

strategy = BestFirstCrawlingStrategy(
    max_depth=2,
    include_external=False,
    max_pages=50,                            # mandatory: unbounded otherwise
    filter_chain=FilterChain([
        URLPatternFilter(patterns=["*/docs/*", "*/guide/*"], reverse=False),
        DomainFilter(allowed_domains=["example.com"]),
        ContentTypeFilter(allowed_types=["text/html"]),
    ]),
    url_scorer=CompositeScorer([KeywordRelevanceScorer(keywords=["api", "reference"], weight=1.0)]),
    score_threshold=0.1,
)
config = CrawlerRunConfig(deep_crawl_strategy=strategy, stream=True)
async for result in await crawler.arun("https://example.com", config=config):
    print(result.metadata.get("depth"), result.url)
```

`[verified: construct]`. `BFSDeepCrawlStrategy` and `DFSDeepCrawlStrategy` accept the same arguments; traversal order is the only difference. With `stream=True`, `arun` yields an async generator.

## 4. Adaptive crawl until a query is covered

```python
from crawl4ai import AdaptiveCrawler, AdaptiveConfig

adaptive = AdaptiveCrawler(
    crawler=crawler,
    config=AdaptiveConfig(max_pages=20, max_depth=3, confidence_threshold=0.7,
                          strategy="statistical", save_state=True,
                          state_path="adaptive-state.json"),   # save_state alone persists nothing
)
state = await adaptive.digest(start_url="https://example.com", query="pricing and limits")
print(adaptive.confidence, adaptive.is_sufficient, len(state.crawled_urls))
print(adaptive.get_relevant_content(top_k=5))
```

`[verified: construct]`. The crawl is query-driven: it stops once coverage/confidence targets for the query are met, ranking links by relevance — this is not change detection; for "fetch only what changed" use §14. `query` is a `digest()` argument, not an `AdaptiveConfig` field; `resume_from` continues an earlier run. `confidence`, `is_sufficient` and `coverage_stats` are properties of `AdaptiveCrawler`. `CrawlState` exposes `crawled_urls`, `knowledge_base`, `metrics`, `query`. Persistence needs both flags — the write is guarded by `save_state and state_path`, so `save_state=True` alone never touches disk `[verified: source]`.

## 5. URL discovery without crawling

```python
from crawl4ai import AsyncUrlSeeder, SeedingConfig

async with AsyncUrlSeeder() as seeder:
    urls = await seeder.urls("example.com", SeedingConfig(
        source="sitemap+cc", pattern="*blog*", live_check=True,
        max_urls=200, hits_per_sec=5, extract_head=True,
        query="machine learning", scoring_method="bm25", score_threshold=0.3))
```

`[verified: construct]`. For full domain structure (subdomains, common paths), use `DomainMapper` with `DomainMapperConfig(source="sitemap+cc+crt+probe")`.

## 6. Session state and authentication

```python
browser_config = BrowserConfig(
    headless=True,
    cookies=[{"name": "session", "value": "abc123", "domain": "example.com"}],
    headers={"Accept-Language": "en-US"},
)
login = CrawlerRunConfig(
    session_id="site-x",
    js_code=["document.querySelector('#user').value='me';",
             "document.querySelector('form').submit();"],
    wait_for="css:.dashboard",
    cache_mode=CacheMode.BYPASS,
)
await crawler.arun("https://example.com/login", config=login)
# subsequent calls reuse session_id="site-x"
```

`[verified: construct]`. `js_code` accepts `str | List[str]`; `cookies` is a list of dicts. For navigation-phase scripting use `crawler.crawler_strategy.set_hook(hook_type, callable)` / `execute_hook(...)`.

## 7. JS-rendered, infinite scroll, lazy images

```python
from crawl4ai import VirtualScrollConfig

config = CrawlerRunConfig(
    wait_for="css:.item",
    scan_full_page=True, scroll_delay=0.3, max_scroll_steps=20,
    virtual_scroll_config=VirtualScrollConfig(
        container_selector="#feed", scroll_count=20,
        scroll_by="container_height", wait_after_scroll=0.7),
    process_iframes=True,
    remove_overlay_elements=True, remove_consent_popups=True,
    cache_mode=CacheMode.BYPASS,
)
```

`[verified: construct]`. `wait_for` requires an explicit readiness signal; retries do not substitute for it.

## 8. Structured records, stable markup

```python
from crawl4ai import JsonCssExtractionStrategy

schema = {"name": "Front page items", "baseSelector": "tr.athing",
          "fields": [{"name": "title", "selector": "span.titleline > a", "type": "text"},
                     {"name": "url", "selector": "span.titleline > a",
                      "type": "attribute", "attribute": "href"}]}
config = CrawlerRunConfig(extraction_strategy=JsonCssExtractionStrategy(schema),
                          cache_mode=CacheMode.BYPASS)
result = await crawler.arun("https://news.ycombinator.com", config=config)
rows = json.loads(result.extracted_content)
```

Result: `[verified: run]` 30 records on 2026-09-27; record 0 `{"title": "\"They had no concept of a duty of care to their users.\"", "url": "https://unsung.aresluna.org/they-had-no-concept-of-a-duty-of-care-to-their-users/"}`. The headline on record 0 differs between runs, so the stable part of this observation is the record shape (title text plus the `href` attribute), not the headline.

Variants: `JsonXPathExtractionStrategy` for XPath selectors; `RegexExtractionStrategy` for emails, prices, URLs over `fit_html`. Field selectors resolve relative to `baseSelector`.

## 9. Structured records, unstable or semantic markup

```python
import os
from crawl4ai import LLMConfig, LLMExtractionStrategy

strategy = LLMExtractionStrategy(
    llm_config=LLMConfig(provider="openai/gpt-4o-mini", api_token=os.environ["OPENAI_API_KEY"]),
    instruction="Extract every pricing plan as {name, monthly_price, seats}.",
    schema={"type": "object", "properties": {"name": {"type": "string"},
                                             "monthly_price": {"type": "number"}}},
    chunk_token_threshold=2048, overlap_rate=0.1, apply_chunking=True, input_format="markdown",
)
result = await crawler.arun(url, config=CrawlerRunConfig(extraction_strategy=strategy))
plans = json.loads(result.extracted_content)
```

`[verified: construct]`. Requires credentials; cost scales with pages and chunk count. Use §8 when the markup is stable.

## 10. Chunks for retrieval

`chunking_strategy` on a run config is consumed by strategies that chunk internally; it does not populate a result field. `[verified: run]` `arun()` with only `chunking_strategy` set leaves `result.extracted_content is None`.

```python
from crawl4ai import DefaultMarkdownGenerator, PruningContentFilterLXML
from crawl4ai.chunking_strategy import OverlappingWindowChunking

config = CrawlerRunConfig(markdown_generator=DefaultMarkdownGenerator(
    content_filter=PruningContentFilterLXML(threshold=0.48)))       # populates markdown.fit_markdown
result = await crawler.arun(url, config=config)
chunks = OverlappingWindowChunking(window_size=1000, overlap=100).chunk(result.markdown.fit_markdown)
```

Result: `[verified: run]` `.chunk()` returns `List[str]`: `OverlappingWindowChunking(window_size=6, overlap=2).chunk("a b c d e. f g h i j. k l m n o. p q r s t.")` (4 five-word sentences) returned 5 chunks. The count follows the window and step (`ceil((words - window_size) / (window_size - overlap)) + 1`), so a shorter sample yields fewer chunks.

Filter choice: `PruningContentFilterLXML` is the maintained pruning filter in 0.9.4; `PruningContentFilter` still produces identical output but emits `DeprecationWarning` `[verified: run]`.

Selection: `RegexChunking` for structural separators; `SlidingWindowChunking`, `FixedLengthWordChunking`, `OverlappingWindowChunking` for size-bounded windows without extra dependencies; `NlpSentenceChunking` needs NLTK `punkt` and fetches it on demand through `model_loader.load_nltk_punkt()`; `TopicSegmentationChunking` needs NLTK `stopwords` and has no such helper — construction raised `LookupError: Resource 'stopwords' not found` on a host without it `[verified: run]` `[verified: source]`.

## 11. Tables

```python
from crawl4ai import DefaultTableExtraction, LLMTableExtraction

config = CrawlerRunConfig(table_extraction=DefaultTableExtraction())              # heuristic
config = CrawlerRunConfig(table_extraction=LLMTableExtraction(llm_config=llm, css_selector="table.pricing"))
```

Result: rows in `result.tables`. `[verified: construct]`

## 12. Proxies, stealth, TLS, PDFs, capture

```python
from crawl4ai import ProxyConfig, RoundRobinProxyStrategy

browser_config = BrowserConfig(
    proxy_config=ProxyConfig(server="http://proxy:8080", username="u", password="p"),
    enable_stealth=True, ignore_https_errors=True, accept_downloads=True, downloads_path="dl")

config = CrawlerRunConfig(
    proxy_rotation_strategy=RoundRobinProxyStrategy(proxies=[ProxyConfig(server="http://p1:8080"),
                                                             ProxyConfig(server="http://p2:8080")]),
    pdf=True, capture_mhtml=True, screenshot=True,
    capture_network_requests=True, capture_console_messages=True)
```

`[verified: construct]`. Adapters are set on the crawler strategy, not on `BrowserConfig`:

```python
from crawl4ai import AsyncWebCrawler, BrowserConfig, UndetectedAdapter
from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy

strategy = AsyncPlaywrightCrawlerStrategy(browser_config=BrowserConfig(headless=True),
                                          browser_adapter=UndetectedAdapter())
async with AsyncWebCrawler(crawler_strategy=strategy) as crawler:
    result = await crawler.arun("https://example.com", config=config)
```

Result: `[verified: run]` `success=True`, `status_code=200`, Markdown 166 chars.

Bot defenses usually require stealth, residential proxies and reduced concurrency together.

## 13. Shell execution

```bash
crwl crawl <url> -o markdown
crwl crawl <url> -s schema.json -e extraction.yml -o json
crwl crawl <url> --deep-crawl bfs --max-pages 20 -o json -O out.json
crwl crawl <url> -q "question about the page"
```

`[verified: construct]` — flags read from `crwl crawl --help` on 0.9.4.

## 14. Re-fetch only changed pages

```python
config = CrawlerRunConfig(cache_mode=CacheMode.ENABLED,     # write on miss, read on the next run
                          check_cache_freshness=True,       # ask the origin before reusing
                          cache_validation_timeout=10.0)
first = await crawler.arun(url, config=config)    # cache_status="miss"
second = await crawler.arun(url, config=config)   # cache_status="hit_validated" on 304
print(second.cache_status, second.cached_at, second.head_fingerprint)
```

Result: `[verified: run]` `https://example.org` on a cold cache: first run `cache_status="miss"`, `cached_at=None`; second run logs `Cache validated: Server returned 304 Not Modified`, reports `cache_status="hit_validated"` with `cached_at` set and a 166-char Markdown. A URL whose copy is already warm (`https://example.com`, once a validating run has written it) reports `cache_status="hit_validated"` on the first call too. Dropping `check_cache_freshness` turns that run into `cache_status="hit"` in 0.005s (2026-09-27): the `[FETCH]` line is still printed, against the local copy at 0.00s, and no `[CACHE]` validation line follows it.

Mechanism: the cached copy is revalidated with conditional requests (`ETag`/`Last-Modified`) and, when the server answers 200 instead of 304, by comparing a fingerprint of the new `<head>` against the stored one `[verified: source]`. `result.head_fingerprint` carries that value.

Scope: this is the change-detection path (`CacheMode.BYPASS` is the 0.9.4 default, so the reuse above is opt-in). `CacheMode.READ_ONLY` reads without writing, `WRITE_ONLY` refreshes without reading. For crawl strategy rather than transport, use §3 with a `FilterChain`. Query-driven saturation crawling is §4, not this.
