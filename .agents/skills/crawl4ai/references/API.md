# Crawl4AI API reference

Purpose: signatures, parameters, defaults, fields, import paths and CLI flags used by this skill.
Source: introspected from the installed package (crawl4ai 0.9.4, 2026-09-27).
Re-check: `python scripts/check_api.py` verifies every name and parameter listed here.

Introspection command:

```bash
python -c "import inspect, importlib.metadata as m, crawl4ai; print(m.version('crawl4ai')); print(inspect.signature(crawl4ai.CrawlerRunConfig))"
```

## Entry points

| Item | Signature |
| --- | --- |
| `AsyncWebCrawler.arun` | `(url: str, config: CrawlerRunConfig = None, **kwargs) -> CrawlResultContainer`; annotated as a container in 0.9.4 but `CrawlResult` attribute access (`success`, `status_code`, `markdown`, `cleaned_html`) works `[verified: run]` |
| `AsyncWebCrawler.arun_many` | `(urls: List[str], config: CrawlerRunConfig \| List[CrawlerRunConfig] \| None = None, dispatcher: BaseDispatcher \| None = None, **kwargs) -> container \| async generator` |
| Other public methods | `aseed_urls`, `amap_domain`, `aprocess_html`, `start`, `close` |
| Construction | `AsyncWebCrawler(crawler_strategy=None, config=None, base_directory=..., thread_safe=False, ...)` |
| Import | `from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode` |

`arun_many` return shape depends on `stream`: awaited call without `stream` yields an iterable container; `stream=True` yields an async generator. `[verified: construct]`

## `CrawlResult`

Model fields (29): `url`, `html`, `fit_html`, `success`, `cleaned_html`, `media`, `links`, `downloaded_files`, `js_execution_result`, `screenshot`, `pdf`, `mhtml`, `extracted_content`, `metadata`, `error_message`, `session_id`, `response_headers`, `status_code`, `ssl_certificate`, `dispatch_result`, `redirected_url`, `redirected_status_code`, `network_requests`, `console_messages`, `tables`, `head_fingerprint`, `cached_at`, `cache_status`, `crawl_stats`

Computed properties: `markdown` (a `MarkdownGenerationResult` exposing `.raw_markdown` and, with a configured content filter, `.fit_markdown`).

## `CacheMode`

Members: `BYPASS` (the `CrawlerRunConfig.cache_mode` default in 0.9.4), `ENABLED`, `DISABLED`, `READ_ONLY`, `WRITE_ONLY`.

`result.cache_status` observed values: `miss`, `hit`, `hit_validated` `[verified: run]`.

Supported run-config controls: `cache_mode`; `check_cache_freshness` (per-run HTTP revalidation, observed `cache_status="hit_validated"` and log `Cache validated: Server returned 304 Not Modified`) `[verified: run]`; `cache_validation_timeout` (default 10.0). The legacy flags `bypass_cache`, `disable_cache`, `no_cache_read`, `no_cache_write` remain in the signature but are rejected — constructing with them or assigning them raises `AttributeError: Setting '<name>' is deprecated. Instead, use cache_mode=CacheMode.<...>` (guarded by `_UNWANTED_PROPS` in `async_configs.py`) `[verified: run]`.

## `CrawlerRunConfig`

100 parameters. Subset used by this skill, grouped:

| Group | Parameters |
| --- | --- |
| Content shaping | `word_count_threshold` (default 1), `css_selector`, `target_elements`, `excluded_tags`, `excluded_selector`, `only_text`, `keep_attrs`, `remove_forms`, `parser_type` (`'lxml'`) |
| Markdown | `markdown_generator` |
| Extraction | `extraction_strategy`, `chunking_strategy` (default `RegexChunking()`), `table_extraction` |
| Cache and session | `cache_mode`, `session_id` |
| Waiting and JS | `wait_until`, `page_timeout`, `wait_for`, `wait_for_timeout`, `js_code` (`str \| List[str]`), `js_code_before_wait`, `js_only`, `c4a_script`, `delay_before_return_html` |
| Scrolling | `scan_full_page`, `scroll_delay`, `max_scroll_steps`, `virtual_scroll_config` (`VirtualScrollConfig \| dict`) |
| Cleanup | `process_iframes`, `flatten_shadow_dom`, `remove_overlay_elements`, `remove_consent_popups` |
| Anti-bot posture | `simulate_user`, `override_navigator`, `magic`, `user_agent`, `user_agent_mode` |
| Capture | `screenshot`, `pdf`, `capture_mhtml`, `capture_network_requests`, `capture_console_messages`, `fetch_ssl_certificate` |
| Links and media | `exclude_external_links`, `exclude_social_media_links`, `exclude_domains`, `exclude_all_images`, `exclude_external_images`, `score_links` |
| Scale and policy | `deep_crawl_strategy`, `url_matcher`, `match_mode`, `check_robots_txt`, `max_retries`, `fallback_fetch_function`, `stream`, `verbose` |
| Proxies | `proxy_config`, `proxy_rotation_strategy`, `proxy_session_id`, `proxy_session_ttl`, `proxy_session_auto_release` |

## `BrowserConfig`

44 parameters. Subset used by this skill, grouped:

| Group | Parameters |
| --- | --- |
| Identity and protocol | `browser_type` (`'chromium'`), `headless` (`True`), `browser_mode` (`'dedicated'`), `cdp_url`, `use_managed_browser`, `browser_context_id`, `create_isolated_context` |
| Session and state | `use_persistent_context`, `user_data_dir`, `chrome_channel`, `storage_state`, `cookies` (list of dicts, e.g. `[{"name": "session", "value": "abc123", "domain": "example.com"}]`), `headers` (dict) |
| Network | `proxy`, `proxy_config`, `ignore_https_errors`, `user_agent`, `user_agent_mode`, `user_agent_generator_config` |
| Rendering | `viewport_width` (1080), `viewport_height` (600), `viewport`, `device_scale_factor`, `java_script_enabled`, `text_mode`, `light_mode`, `memory_saving_mode`, `max_pages_before_recycle`, `extra_args`, `init_scripts` |
| Stealth | `enable_stealth`, `avoid_ads`, `avoid_css` |
| Diagnostics | `verbose`, `debugging_port`, `sleep_on_close` |

## Dispatchers

| Class | Signature |
| --- | --- |
| `MemoryAdaptiveDispatcher` | `(memory_threshold_percent=90.0, critical_threshold_percent=95.0, recovery_threshold_percent=85.0, check_interval=1.0, max_session_permit=20, fairness_timeout=600.0, memory_wait_timeout=600.0, rate_limiter=None, monitor=None)` |
| `SemaphoreDispatcher` | `(semaphore_count=5, max_session_permit=20, rate_limiter=None, monitor=None)` |
| `RateLimiter` | `(base_delay=(1.0, 3.0), max_delay=60.0, max_retries=3, rate_limit_codes=None)` |
| `CrawlerMonitor` | `(urls_total=0, refresh_rate=1.0, enable_ui=True, max_width=120)` |

Per-result dispatch data: `result.dispatch_result`; batch statistics: `result.crawl_stats`.

## Deep crawling

| Class | Parameters |
| --- | --- |
| `BFSDeepCrawlStrategy`, `DFSDeepCrawlStrategy`, `BestFirstCrawlingStrategy` | `max_depth`, `include_external`, `max_pages`, `filter_chain`, `url_scorer`, `score_threshold` |
| `FilterChain` | `(filters: List[URLFilter] = None)` |
| Filters | `URLPatternFilter(patterns, use_glob=True, reverse=False)`, `ContentTypeFilter(allowed_types, check_extension=True, ...)`, `DomainFilter(allowed_domains=None, blocked_domains=None)`, `SEOFilter(threshold=0.65, keywords=None, weights=None)` |
| Scorers | `KeywordRelevanceScorer(keywords, weight=...)`, `PathDepthScorer(...)`, `DomainAuthorityScorer(...)`, `FreshnessScorer(...)`, `ContentTypeScorer(...)`, `CompositeScorer(list)` |

Import paths: `crawl4ai` (re-exported), `crawl4ai.deep_crawling`, `crawl4ai.deep_crawling.filters`, `crawl4ai.deep_crawling.scorers`.

## Extraction

| Strategy | Signature |
| --- | --- |
| `JsonCssExtractionStrategy` | `(schema: Dict[str, Any], **kwargs)` |
| `JsonXPathExtractionStrategy` | `(schema: Dict[str, Any], **kwargs)` |
| `JsonLxmlExtractionStrategy` | LXML variant, same call shape |
| `RegexExtractionStrategy` | `(pattern=<built-in enum>, *, custom=None, input_format='fit_html', **kwargs)` |
| `LLMExtractionStrategy` | `(llm_config=None, instruction=None, schema=None, extraction_type='schema', chunk_token_threshold=2048, overlap_rate=0.1, word_token_rate=1.3, apply_chunking=True, input_format='markdown', force_json_response=False, verbose=False, provider='openai/gpt-4o', api_token=None, base_url=None, api_base=None, **kwargs)` |
| `LLMConfig` | `(provider='openai/gpt-4o', api_token=None, base_url=None, temperature=None, max_tokens=None, top_p=None, frequency_penalty=None, presence_penalty=None, stop=None, n=None, backoff_base_delay=None, backoff_max_attempts=None, backoff_exponential_factor=None)` |
| `DefaultTableExtraction` | `(**kwargs)` |
| `LLMTableExtraction` | `(llm_config=None, css_selector=None, max_tries=3, enable_chunking=True, chunk_token_threshold=3000, min_rows_per_chunk=10, max_parallel_chunks=5, verbose=False, **kwargs)` |
| `NoTableExtraction` | disables table extraction |

Schema shape: `{"name": str, "baseSelector": str, "fields": [{"name": str, "selector": str, "type": "text"|"attribute"|"html"|"nested"|"list", "attribute"?: str}]}`. Field selectors resolve relative to `baseSelector`.

## Chunking

Import path `crawl4ai.chunking_strategy` for all; only `RegexChunking` is re-exported from `crawl4ai`.

| Class | Signature | Extra dependency |
| --- | --- | --- |
| `RegexChunking` | `(patterns=None)` (default `[r'\n\n']`) | none |
| `SlidingWindowChunking` | `(window_size=100, step=50, **kwargs)` | none |
| `FixedLengthWordChunking` | `(chunk_size=100, **kwargs)` | none |
| `OverlappingWindowChunking` | `(window_size=1000, overlap=100, **kwargs)` | none |
| `NlpSentenceChunking` | `(**kwargs)` | NLTK `punkt`; `__init__` calls `model_loader.load_nltk_punkt()`, which finds the resource and otherwise downloads it — construction succeeded on a host without it, and raises `LookupError` only when the download cannot run `[verified: run]` `[verified: source]` |
| `TopicSegmentationChunking` | `(num_keywords=3, **kwargs)` | NLTK `stopwords` (TextTiling); no download helper, so construction raises `LookupError: Resource 'stopwords' not found` when the resource is missing `[verified: run]` |
| `IdentityChunking` | `(**kwargs)` | none |

Method: `.chunk(text) -> List[str]`. `[verified: run]` `OverlappingWindowChunking(window_size=6, overlap=2).chunk(<4-sentence text>)` returned 5 chunks.

## Content filters

| Class | Signature |
| --- | --- |
| `PruningContentFilterLXML` | `(user_query=None, min_word_threshold=None, threshold_type='fixed', threshold=0.48)`; the maintained pruning filter in 0.9.4 |
| `PruningContentFilter` | `(user_query=None, min_word_threshold=None, threshold_type='fixed', threshold=0.48, preserve_classes=None, preserve_tags=None)`; deprecated in 0.9.4 in favour of `PruningContentFilterLXML` ("~10x faster with identical output"; will become an alias) — constructing it emits `DeprecationWarning` `[verified: run]` |
| `BM25ContentFilter` | `(user_query=None, bm25_threshold=1.0, language='english', use_stemming=True)` |
| `LLMContentFilter` | LLM-driven filter |
| `DefaultMarkdownGenerator` | `(content_filter=None, options=None, content_source='cleaned_html')` |

## Adaptive crawling and discovery

| Class | Signature |
| --- | --- |
| `AdaptiveCrawler` | `(crawler=None, config=None, strategy=None)`; `digest(start_url, query, resume_from=None) -> CrawlState`; `get_relevant_content(top_k=5) -> List[Dict]`; properties `confidence`, `is_sufficient`, `coverage_stats` |
| `AdaptiveConfig` | `(confidence_threshold=0.7, max_depth=5, max_pages=20, top_k_links=3, min_gain_threshold=0.1, strategy='statistical', saturation_threshold=0.8, consistency_threshold=0.7, save_state=False, state_path=None, embedding_model='sentence-transformers/all-MiniLM-L6-v2', ...)`; no `query` parameter — the query belongs to `digest()` |
| `CrawlState` fields | `crawled_urls`, `knowledge_base`, `pending_links`, `query`, `metrics`, `total_documents`, `crawl_order`, `kb_embeddings`, `expanded_queries`, `semantic_gaps`, `embedding_model`, ... |
| `AsyncUrlSeeder` | `(ttl=timedelta(days=7), client=None, logger=None, base_directory=None, cache_root=None)`; async context manager; `urls(domain, config) -> List[Dict]`, `many_urls(...)`, `extract_head_for_urls(...)` |
| `SeedingConfig` | `(source='sitemap+cc', pattern='*', live_check=False, extract_head=False, max_urls=-1, concurrency=1000, hits_per_sec=5, force=False, query=None, score_threshold=None, scoring_method='bm25', filter_nonsense_urls=True, cache_ttl_hours=24, validate_sitemap_lastmod=True)` |
| `DomainMapper` | `(client=None, logger=None, base_directory=None)`; `DomainMapperConfig(source='sitemap+cc+crt+probe', max_urls=-1, concurrency=50, hits_per_sec=10, extract_head=True, probe_paths=None, include_subdomains=True, dns_timeout=3.0, http_timeout=10.0, ...)` |

## Browser adapters and proxies

`BrowserAdapter` is abstract; the concrete adapters are `PlaywrightAdapter` (used by default) and `UndetectedAdapter` (patchright stealth). Adapters are injected through the crawler strategy, not through `BrowserConfig`: `AsyncPlaywrightCrawlerStrategy(browser_config=..., browser_adapter=...)` — full call in `references/PATTERNS.md` §12 `[verified: run]`.

`AsyncPlaywrightCrawlerStrategy(browser_config=None, logger=None, browser_adapter=None, **kwargs)` also exposes `set_hook(hook_type: str, hook: Callable)` and `execute_hook(hook_type, *args, **kwargs)`.

Proxies: `ProxyConfig(server, username=None, password=None, ip=None)`; `RoundRobinProxyStrategy(proxies=[...])` (assigned to `CrawlerRunConfig.proxy_rotation_strategy`).

## PDF handling

| Item | Value |
| --- | --- |
| Embedded or direct PDF capture | `CrawlerRunConfig(pdf=True)` → `result.pdf`; `capture_mhtml=True` → `result.mhtml` |
| PDF URL scraping | `from crawl4ai.processors.pdf import PDFContentScrapingStrategy, NaivePDFProcessorStrategy, PDFCrawlerStrategy` |
| Limits | `DEFAULT_MAX_PDF_PAGES`, `DEFAULT_MAX_PDF_BYTES`, `DEFAULT_MAX_REDIRECTS` |

## CLI (`crwl`, Click group)

```bash
crwl crawl <url> -o markdown
crwl crawl <url> -o json -bc -v
crwl crawl <url> -s schema.json -e extraction.yml -o json
crwl crawl <url> --deep-crawl bfs --max-pages 20
crwl crawl <url> -q "question about the page"
crwl crawl <url> -c "css_selector=main,word_count_threshold=5"    # run-config key=value
crwl crawl <url> -b "headless=true,viewport_width=1280"           # browser-config key=value
```

| Flag | Meaning |
| --- | --- |
| `-B/-C/-f/-e` | browser, crawler, content-filter, extraction config file (YAML/JSON) |
| `-s` | JSON schema for extraction |
| `-j` | LLM extraction with optional description |
| `-o` | `all` \| `json` \| `markdown` \| `md` \| `markdown-fit` \| `md-fit` |
| `-O` | output file path (default stdout) |
| `-bc` | bypass cache |
| `-q` | question about the crawled content |
| `-p` | browser profile by name |
| `--deep-crawl`, `--max-pages` | deep crawl strategy and page cap |
| `-v` | verbose |
