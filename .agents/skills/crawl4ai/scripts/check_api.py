#!/usr/bin/env python3
"""Verify that every crawl4ai API referenced by this skill exists in the installed package.

Purpose: detect drift between the skill's instructions and the installed crawl4ai version.
Method: import the package; assert each import path, class, method, config parameter and
CrawlResult field the skill references is present, and that the legacy cache flags the
skill documents as rejected still raise. No network access, no crawling.

Usage:
    python scripts/check_api.py                    # text report on stdout, diagnostics on stderr
    python scripts/check_api.py --json             # JSON report on stdout
    python scripts/check_api.py --max-problems 10  # bound the text report

Exit codes: 0 = all referenced APIs present, 1 = drift detected, 2 = crawl4ai not importable.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.metadata as metadata
import inspect
import json
import sys

# (module, attribute) — the import paths and names used across SKILL.md and references/
# --- generated: imports (scripts/update_skill.py unions the curated list with cited names) ---
IMPORTS = [
    ("crawl4ai", "AsyncWebCrawler"),
    ("crawl4ai", "BrowserConfig"),
    ("crawl4ai", "CrawlerRunConfig"),
    ("crawl4ai", "CrawlResult"),
    ("crawl4ai", "CacheMode"),
    ("crawl4ai", "MemoryAdaptiveDispatcher"),
    ("crawl4ai", "SemaphoreDispatcher"),
    ("crawl4ai", "RateLimiter"),
    ("crawl4ai", "CrawlerMonitor"),
    ("crawl4ai", "BFSDeepCrawlStrategy"),
    ("crawl4ai", "DFSDeepCrawlStrategy"),
    ("crawl4ai", "BestFirstCrawlingStrategy"),
    ("crawl4ai", "FilterChain"),
    ("crawl4ai", "JsonCssExtractionStrategy"),
    ("crawl4ai", "JsonXPathExtractionStrategy"),
    ("crawl4ai", "LLMExtractionStrategy"),
    ("crawl4ai", "LLMConfig"),
    ("crawl4ai", "RegexExtractionStrategy"),
    ("crawl4ai", "DefaultMarkdownGenerator"),
    ("crawl4ai", "PruningContentFilter"),
    ("crawl4ai", "BM25ContentFilter"),
    ("crawl4ai", "VirtualScrollConfig"),
    ("crawl4ai", "ProxyConfig"),
    ("crawl4ai", "RoundRobinProxyStrategy"),
    ("crawl4ai", "DefaultTableExtraction"),
    ("crawl4ai", "LLMTableExtraction"),
    ("crawl4ai", "AdaptiveCrawler"),
    ("crawl4ai", "AdaptiveConfig"),
    ("crawl4ai", "AsyncUrlSeeder"),
    ("crawl4ai", "SeedingConfig"),
    ("crawl4ai", "DomainMapper"),
    ("crawl4ai", "DomainMapperConfig"),
    ("crawl4ai", "UndetectedAdapter"),
    ("crawl4ai", "LXMLWebScrapingStrategy"),
    ("crawl4ai.chunking_strategy", "RegexChunking"),
    ("crawl4ai.chunking_strategy", "SlidingWindowChunking"),
    ("crawl4ai.chunking_strategy", "FixedLengthWordChunking"),
    ("crawl4ai.chunking_strategy", "OverlappingWindowChunking"),
    ("crawl4ai.chunking_strategy", "NlpSentenceChunking"),
    ("crawl4ai.chunking_strategy", "TopicSegmentationChunking"),
    ("crawl4ai.deep_crawling.filters", "URLPatternFilter"),
    ("crawl4ai.deep_crawling.filters", "DomainFilter"),
    ("crawl4ai.deep_crawling.filters", "ContentTypeFilter"),
    ("crawl4ai.deep_crawling.scorers", "KeywordRelevanceScorer"),
    ("crawl4ai.deep_crawling.scorers", "CompositeScorer"),
    ("crawl4ai.processors.pdf", "PDFContentScrapingStrategy"),
    ("crawl4ai", "PruningContentFilterLXML"),
    ("crawl4ai", "NoTableExtraction"),
    ("crawl4ai", "LLMContentFilter"),
    ("crawl4ai", "JsonLxmlExtractionStrategy"),
    ("crawl4ai", "MarkdownGenerationResult"),
    ("crawl4ai", "CrawlState"),
    ("crawl4ai", "BaseDispatcher"),
    ("crawl4ai", "BrowserAdapter"),
    ("crawl4ai", "PlaywrightAdapter"),
    ("crawl4ai", "SEOFilter"),
    ("crawl4ai", "URLFilter"),
    ("crawl4ai", "PathDepthScorer"),
    ("crawl4ai", "DomainAuthorityScorer"),
    ("crawl4ai", "FreshnessScorer"),
    ("crawl4ai", "ContentTypeScorer"),
    ("crawl4ai.chunking_strategy", "IdentityChunking"),
    ("crawl4ai.async_crawler_strategy", "AsyncPlaywrightCrawlerStrategy"),
    ("crawl4ai.processors.pdf", "NaivePDFProcessorStrategy"),
    ("crawl4ai.processors.pdf", "PDFCrawlerStrategy"),
    ("crawl4ai.processors.pdf", "DEFAULT_MAX_PDF_BYTES"),
    ("crawl4ai.processors.pdf", "DEFAULT_MAX_PDF_PAGES"),
    ("crawl4ai.processors.pdf", "DEFAULT_MAX_REDIRECTS"),

]

# Config parameters the skill's recipes pass
# --- generated: run_params (scripts/update_skill.py unions the curated list with cited names) ---
RUN_CONFIG_PARAMS = [
    "word_count_threshold", "css_selector", "target_elements", "excluded_tags", "only_text",
    "markdown_generator", "extraction_strategy", "chunking_strategy", "table_extraction",
    "cache_mode", "session_id", "wait_for", "wait_until", "page_timeout", "js_code",
    "js_only", "delay_before_return_html", "scan_full_page", "scroll_delay",
    "virtual_scroll_config", "process_iframes", "remove_overlay_elements",
    "remove_consent_popups", "simulate_user", "magic", "screenshot", "pdf",
    "capture_mhtml", "capture_network_requests", "capture_console_messages",
    "proxy_rotation_strategy", "proxy_config", "deep_crawl_strategy", "stream",
    "exclude_external_links", "check_robots_txt", "max_retries", "verbose",
    "excluded_selector", "keep_attrs", "remove_forms", "parser_type", "c4a_script", "js_code_before_wait",
    "wait_for_timeout", "max_scroll_steps", "flatten_shadow_dom", "override_navigator", "user_agent",
    "user_agent_mode", "user_agent_generator_config", "fetch_ssl_certificate", "exclude_social_media_links",
    "exclude_domains", "exclude_all_images", "exclude_external_images", "score_links", "url_matcher", "match_mode",
    "fallback_fetch_function", "proxy_session_id", "proxy_session_ttl", "proxy_session_auto_release",
    "check_cache_freshness", "cache_validation_timeout",
]
# --- generated: browser_params (scripts/update_skill.py unions the curated list with cited names) ---
BROWSER_CONFIG_PARAMS = [
    "browser_type", "headless", "browser_mode", "cdp_url", "use_persistent_context",
    "user_data_dir", "chrome_channel", "storage_state", "cookies", "headers",
    "proxy", "proxy_config", "ignore_https_errors", "java_script_enabled",
    "viewport_width", "viewport_height", "text_mode", "light_mode", "extra_args",
    "enable_stealth", "accept_downloads", "downloads_path", "verbose",
    "use_managed_browser", "browser_context_id", "create_isolated_context", "viewport", "device_scale_factor",
    "memory_saving_mode", "max_pages_before_recycle", "init_scripts", "avoid_ads", "avoid_css",
    "user_agent", "user_agent_mode", "user_agent_generator_config", "debugging_port", "sleep_on_close",
]
# methods/attributes the recipes call
# --- generated: methods (scripts/update_skill.py unions the curated list with cited names) ---
METHODS = [
    ("crawl4ai", "AsyncWebCrawler", "arun"),
    ("crawl4ai", "AsyncWebCrawler", "arun_many"),
    ("crawl4ai", "AdaptiveCrawler", "digest"),
    ("crawl4ai", "AdaptiveCrawler", "get_relevant_content"),
    ("crawl4ai", "AdaptiveCrawler", "confidence"),
    ("crawl4ai", "AdaptiveCrawler", "is_sufficient"),
    ("crawl4ai", "AdaptiveCrawler", "coverage_stats"),
    ("crawl4ai", "AsyncUrlSeeder", "urls"),
    ("crawl4ai.async_crawler_strategy", "AsyncPlaywrightCrawlerStrategy", "set_hook"),
    ("crawl4ai.async_crawler_strategy", "AsyncPlaywrightCrawlerStrategy", "execute_hook"),
    ("crawl4ai.chunking_strategy", "RegexChunking", "chunk"),
    ("crawl4ai.chunking_strategy", "OverlappingWindowChunking", "chunk"),
    ("crawl4ai", "CacheMode", "BYPASS"),
    ("crawl4ai", "CacheMode", "DISABLED"),
    ("crawl4ai", "CacheMode", "ENABLED"),
    ("crawl4ai", "CacheMode", "READ_ONLY"),

]

# CrawlResult fields the skill documents — API.md lists all 29
# --- generated: result_fields (scripts/update_skill.py unions the curated list with cited names) ---
RESULT_FIELDS = [
    "url", "html", "fit_html", "success", "cleaned_html", "media", "links", "downloaded_files",
    "js_execution_result", "screenshot", "pdf", "mhtml", "extracted_content", "metadata", "error_message",
    "session_id", "response_headers", "status_code", "ssl_certificate", "dispatch_result", "redirected_url",
    "redirected_status_code", "network_requests", "console_messages", "tables", "head_fingerprint", "cached_at",
    "cache_status", "crawl_stats",
]

# Legacy cache flags API.md documents as rejected; each must still raise the deprecation AttributeError
REJECTED_RUN_CONFIG_PARAMS = ["bypass_cache", "disable_cache", "no_cache_read", "no_cache_write"]

# Defaults the references state. A version that changes one of these invalidates the reference tables,
# so the gate fails instead of letting a stale value be published.
DEFAULTS: tuple[tuple[str, str, object], ...] = (
    ("CrawlerRunConfig", "cache_mode", "CacheMode.BYPASS"),
    ("CrawlerRunConfig", "word_count_threshold", 1),
    ("CrawlerRunConfig", "parser_type", "lxml"),
    ("BrowserConfig", "browser_type", "chromium"),
    ("BrowserConfig", "headless", True),
    ("BrowserConfig", "browser_mode", "dedicated"),
    ("BrowserConfig", "viewport_width", 1080),
    ("BrowserConfig", "viewport_height", 600),
    ("MemoryAdaptiveDispatcher", "memory_threshold_percent", 90.0),
    ("MemoryAdaptiveDispatcher", "critical_threshold_percent", 95.0),
    ("MemoryAdaptiveDispatcher", "recovery_threshold_percent", 85.0),
    ("MemoryAdaptiveDispatcher", "check_interval", 1.0),
    ("MemoryAdaptiveDispatcher", "max_session_permit", 20),
    ("MemoryAdaptiveDispatcher", "fairness_timeout", 600.0),
    ("MemoryAdaptiveDispatcher", "memory_wait_timeout", 600.0),
    ("SemaphoreDispatcher", "semaphore_count", 5),
    ("RateLimiter", "max_delay", 60.0),
    ("RateLimiter", "max_retries", 3),
    ("RateLimiter", "rate_limit_codes", None),
    ("CrawlerMonitor", "urls_total", 0),
    ("CrawlerMonitor", "refresh_rate", 1.0),
    ("CrawlerMonitor", "enable_ui", True),
    ("CrawlerMonitor", "max_width", 120),
    ("URLPatternFilter", "use_glob", True),
    ("URLPatternFilter", "reverse", False),
    ("DomainFilter", "allowed_domains", None),
    ("DomainFilter", "blocked_domains", None),
    ("ContentTypeFilter", "check_extension", True),
    ("SEOFilter", "threshold", 0.65),
    ("KeywordRelevanceScorer", "weight", 1.0),
    ("CompositeScorer", "normalize", True),
    ("FilterChain", "filters", None),
    ("VirtualScrollConfig", "scroll_count", 10),
    ("VirtualScrollConfig", "scroll_by", "container_height"),
    ("VirtualScrollConfig", "wait_after_scroll", 0.5),
    ("RegexChunking", "patterns", None),
    ("SlidingWindowChunking", "window_size", 100),
    ("SlidingWindowChunking", "step", 50),
    ("FixedLengthWordChunking", "chunk_size", 100),
    ("OverlappingWindowChunking", "window_size", 1000),
    ("OverlappingWindowChunking", "overlap", 100),
    ("RegexExtractionStrategy", "input_format", "fit_html"),
    ("LLMConfig", "provider", "openai/gpt-4o"),
    ("LLMExtractionStrategy", "llm_config", None),
    ("LLMExtractionStrategy", "extraction_type", "schema"),
    ("LLMExtractionStrategy", "chunk_token_threshold", 2048),
    ("LLMExtractionStrategy", "overlap_rate", 0.1),
    ("LLMExtractionStrategy", "word_token_rate", 1.3),
    ("LLMExtractionStrategy", "apply_chunking", True),
    ("LLMExtractionStrategy", "input_format", "markdown"),
    ("LLMExtractionStrategy", "force_json_response", False),
    ("LLMExtractionStrategy", "provider", "openai/gpt-4o"),
    ("LLMTableExtraction", "llm_config", None),
    ("LLMTableExtraction", "max_tries", 3),
    ("LLMTableExtraction", "enable_chunking", True),
    ("LLMTableExtraction", "chunk_token_threshold", 3000),
    ("LLMTableExtraction", "min_rows_per_chunk", 10),
    ("LLMTableExtraction", "max_parallel_chunks", 5),
    ("PruningContentFilter", "threshold_type", "fixed"),
    ("PruningContentFilter", "threshold", 0.48),
    ("PruningContentFilterLXML", "threshold_type", "fixed"),
    ("PruningContentFilterLXML", "threshold", 0.48),
    ("BM25ContentFilter", "bm25_threshold", 1.0),
    ("BM25ContentFilter", "language", "english"),
    ("BM25ContentFilter", "use_stemming", True),
    ("DefaultMarkdownGenerator", "content_filter", None),
    ("DefaultMarkdownGenerator", "content_source", "cleaned_html"),
    ("ProxyConfig", "username", None),
    ("ProxyConfig", "password", None),
    ("ProxyConfig", "ip", None),
    ("AdaptiveConfig", "confidence_threshold", 0.7),
    ("AdaptiveConfig", "max_depth", 5),
    ("AdaptiveConfig", "max_pages", 20),
    ("AdaptiveConfig", "top_k_links", 3),
    ("AdaptiveConfig", "min_gain_threshold", 0.1),
    ("AdaptiveConfig", "strategy", "statistical"),
    ("AdaptiveConfig", "saturation_threshold", 0.8),
    ("AdaptiveConfig", "consistency_threshold", 0.7),
    ("AdaptiveConfig", "save_state", False),
    ("AdaptiveConfig", "state_path", None),
    ("AdaptiveConfig", "embedding_model", "sentence-transformers/all-MiniLM-L6-v2"),
    ("SeedingConfig", "source", "sitemap+cc"),
    ("SeedingConfig", "pattern", "*"),
    ("SeedingConfig", "live_check", False),
    ("SeedingConfig", "extract_head", False),
    ("SeedingConfig", "max_urls", -1),
    ("SeedingConfig", "concurrency", 1000),
    ("SeedingConfig", "hits_per_sec", 5),
    ("SeedingConfig", "force", False),
    ("SeedingConfig", "scoring_method", "bm25"),
    ("SeedingConfig", "filter_nonsense_urls", True),
    ("SeedingConfig", "cache_ttl_hours", 24),
    ("SeedingConfig", "validate_sitemap_lastmod", True),
    ("DomainMapperConfig", "source", "sitemap+cc+crt+probe"),
    ("DomainMapperConfig", "max_urls", -1),
    ("DomainMapperConfig", "concurrency", 50),
    ("DomainMapperConfig", "hits_per_sec", 10),
    ("DomainMapperConfig", "extract_head", True),
    ("DomainMapperConfig", "include_subdomains", True),
    ("DomainMapperConfig", "dns_timeout", 3.0),
    ("DomainMapperConfig", "http_timeout", 10.0),
    ("AsyncPlaywrightCrawlerStrategy", "browser_config", None),
    ("AsyncPlaywrightCrawlerStrategy", "logger", None),
    ("AsyncPlaywrightCrawlerStrategy", "browser_adapter", None),
)


def default_matches(actual: object, expected: object) -> bool:
    """Compare an introspected default with the value a reference states.

    `CacheMode.BYPASS` in the table means the enum member of that name, not the literal string.
    """
    if isinstance(expected, str) and "." in expected:
        holder, _, member = expected.partition(".")
        return type(actual).__name__ == holder and getattr(actual, "name", None) == member
    return actual == expected


def check() -> tuple[dict, int]:
    problems: list[str] = []
    try:
        version = metadata.version("crawl4ai")
    except metadata.PackageNotFoundError:
        print("error: crawl4ai is not importable (expected 0.9.x); install with: pip install crawl4ai",
              file=sys.stderr)
        return {}, 2

    for module_name, attr in IMPORTS:
        try:
            module = importlib.import_module(module_name)
        except ImportError as exc:
            problems.append(f"cannot import {module_name}: {exc}")
            continue
        if not hasattr(module, attr):
            problems.append(f"{module_name}.{attr} is missing")

    import crawl4ai  # noqa: E402  (after the importability check above)

    for name, params in (("CrawlerRunConfig", RUN_CONFIG_PARAMS), ("BrowserConfig", BROWSER_CONFIG_PARAMS)):
        cls = getattr(crawl4ai, name, None)
        if cls is None:
            continue
        available = set(inspect.signature(cls).parameters)
        for param in params:
            if param not in available:
                problems.append(f"{name}({param}) is missing")

    for class_name, param, expected in DEFAULTS:
        cls = getattr(crawl4ai, class_name, None)
        if cls is None:
            continue  # an absent class is already reported through IMPORTS
        parameters = inspect.signature(cls).parameters
        if param not in parameters:
            problems.append(f"{class_name}({param}) is missing")
            continue
        actual = parameters[param].default
        if not default_matches(actual, expected):
            problems.append(f"{class_name}({param}) default changed: expected {expected!r}, got {actual!r}")

    for module_name, cls_name, attr in METHODS:
        try:
            holder = getattr(importlib.import_module(module_name), cls_name)
        except (ImportError, AttributeError):
            continue
        if not hasattr(holder, attr):
            problems.append(f"{module_name}.{cls_name}.{attr} is missing")

    result_fields = list(getattr(crawl4ai.CrawlResult, "model_fields", {}) or {})
    for field in RESULT_FIELDS:
        if field not in result_fields:
            problems.append(f"CrawlResult.{field} is missing")
    if not isinstance(getattr(crawl4ai.CrawlResult, "markdown", None), property):
        problems.append("CrawlResult.markdown property is missing")   # computed, not a model field

    for param in REJECTED_RUN_CONFIG_PARAMS:
        try:
            crawl4ai.CrawlerRunConfig(**{param: True})
        except AttributeError as exc:
            if "deprecated" not in str(exc):
                problems.append(f"CrawlerRunConfig({param}) failed without the deprecation message: {exc}")
        except Exception as exc:   # noqa: BLE001  (TypeError/ValidationError both mean the documented rejection changed)
            problems.append(f"CrawlerRunConfig({param}) raised {type(exc).__name__} "
                            f"instead of the deprecation AttributeError: {exc}")
        else:
            problems.append(f"CrawlerRunConfig({param}) is accepted again; the skill documents it as rejected")

    report = {
        "crawl4ai_version": version,
        "expected": "0.9.x",
        "version_ok": version.startswith("0.9."),
        "checked": {"imports": len(IMPORTS), "params": len(RUN_CONFIG_PARAMS) + len(BROWSER_CONFIG_PARAMS),
                    "methods": len(METHODS), "result_fields": len(RESULT_FIELDS),
                    "rejected_params": len(REJECTED_RUN_CONFIG_PARAMS), "defaults": len(DEFAULTS)},
        "problems": problems,
    }
    return report, (1 if problems else 0)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify that every crawl4ai API referenced by this skill exists in the installed package.",
        epilog="Exit codes:\n"
        "  0  all referenced APIs present\n"
        "  1  drift detected (missing name, parameter, method or result field)\n"
        "  2  crawl4ai not importable\n"
        "\nExamples:\n"
        "  python scripts/check_api.py\n"
        "  python scripts/check_api.py --json\n"
        "  python scripts/check_api.py --max-problems 10",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--json", action="store_true", help="print the report as JSON on stdout")
    parser.add_argument("--max-problems", type=int, default=50,
                        help="cap the number of problems listed in the text report (default: 50; use --json for all)")
    args = parser.parse_args()

    report, code = check()
    if not report:
        return code
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"crawl4ai: {report['crawl4ai_version']} (skill expects {report['expected']}: "
              f"{'match' if report['version_ok'] else 'mismatch'})")
        print(f"checked: {report['checked']}")
        if report["problems"]:
            problems = report["problems"]
            print(f"drift: {len(problems)} referenced API(s) missing")
            for problem in problems[: args.max_problems]:
                print(f"  - {problem}")
            if len(problems) > args.max_problems:
                print(f"  ... {len(problems) - args.max_problems} more (--json for the full list)")
            print("action: treat the installed package as source of truth and report the drift",
                  file=sys.stderr)
        else:
            print("drift: none (all referenced APIs present)")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
