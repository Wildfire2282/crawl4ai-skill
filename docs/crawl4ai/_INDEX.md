# Documentation mirror — unclecode/crawl4ai docs/md_v2

Mirror of <https://github.com/unclecode/crawl4ai/tree/develop/docs/md_v2>, taken 2026-09-27 by `scripts/sync_docs_repo.py` (project tool; independent of any agent skill).
48 pages from commit `1f68e5bd` (2026-09-25); page bodies are the upstream Markdown, with sibling-page links re-pointed at their docs.crawl4ai.com URL.
Pages outside `SECTIONS` in `scripts/sync_docs_repo.py`, or listed in its `CURATED_OUT`, are not carried (44 upstream page(s) excluded by policy) — see below.
Files are flat (`<section>-<page>.md`) so every reference stays one level deep.

Refresh from the project root:

```bash
python scripts/sync_docs_repo.py
python scripts/sync_docs_repo.py --check     # is there upstream work at all? one request, no download
python scripts/sync_docs_repo.py --reindex   # offline: apply the policy and rebuild this index
```

## advanced

| Local file | Upstream | Site |
| --- | --- | --- |
| [`advanced-adaptive-strategies.md`](./advanced-adaptive-strategies.md) | `docs/md_v2/advanced/adaptive-strategies.md` | <https://docs.crawl4ai.com/advanced/adaptive-strategies/> |
| [`advanced-advanced-features.md`](./advanced-advanced-features.md) | `docs/md_v2/advanced/advanced-features.md` | <https://docs.crawl4ai.com/advanced/advanced-features/> |
| [`advanced-anti-bot-and-fallback.md`](./advanced-anti-bot-and-fallback.md) | `docs/md_v2/advanced/anti-bot-and-fallback.md` | <https://docs.crawl4ai.com/advanced/anti-bot-and-fallback/> |
| [`advanced-file-downloading.md`](./advanced-file-downloading.md) | `docs/md_v2/advanced/file-downloading.md` | <https://docs.crawl4ai.com/advanced/file-downloading/> |
| [`advanced-hooks-auth.md`](./advanced-hooks-auth.md) | `docs/md_v2/advanced/hooks-auth.md` | <https://docs.crawl4ai.com/advanced/hooks-auth/> |
| [`advanced-identity-based-crawling.md`](./advanced-identity-based-crawling.md) | `docs/md_v2/advanced/identity-based-crawling.md` | <https://docs.crawl4ai.com/advanced/identity-based-crawling/> |
| [`advanced-lazy-loading.md`](./advanced-lazy-loading.md) | `docs/md_v2/advanced/lazy-loading.md` | <https://docs.crawl4ai.com/advanced/lazy-loading/> |
| [`advanced-multi-url-crawling.md`](./advanced-multi-url-crawling.md) | `docs/md_v2/advanced/multi-url-crawling.md` | <https://docs.crawl4ai.com/advanced/multi-url-crawling/> |
| [`advanced-network-console-capture.md`](./advanced-network-console-capture.md) | `docs/md_v2/advanced/network-console-capture.md` | <https://docs.crawl4ai.com/advanced/network-console-capture/> |
| [`advanced-pdf-parsing.md`](./advanced-pdf-parsing.md) | `docs/md_v2/advanced/pdf-parsing.md` | <https://docs.crawl4ai.com/advanced/pdf-parsing/> |
| [`advanced-proxy-security.md`](./advanced-proxy-security.md) | `docs/md_v2/advanced/proxy-security.md` | <https://docs.crawl4ai.com/advanced/proxy-security/> |
| [`advanced-session-management.md`](./advanced-session-management.md) | `docs/md_v2/advanced/session-management.md` | <https://docs.crawl4ai.com/advanced/session-management/> |
| [`advanced-ssl-certificate.md`](./advanced-ssl-certificate.md) | `docs/md_v2/advanced/ssl-certificate.md` | <https://docs.crawl4ai.com/advanced/ssl-certificate/> |
| [`advanced-undetected-browser.md`](./advanced-undetected-browser.md) | `docs/md_v2/advanced/undetected-browser.md` | <https://docs.crawl4ai.com/advanced/undetected-browser/> |
| [`advanced-virtual-scroll.md`](./advanced-virtual-scroll.md) | `docs/md_v2/advanced/virtual-scroll.md` | <https://docs.crawl4ai.com/advanced/virtual-scroll/> |

## api

| Local file | Upstream | Site |
| --- | --- | --- |
| [`api-adaptive-crawler.md`](./api-adaptive-crawler.md) | `docs/md_v2/api/adaptive-crawler.md` | <https://docs.crawl4ai.com/api/adaptive-crawler/> |
| [`api-arun.md`](./api-arun.md) | `docs/md_v2/api/arun.md` | <https://docs.crawl4ai.com/api/arun/> |
| [`api-arun_many.md`](./api-arun_many.md) | `docs/md_v2/api/arun_many.md` | <https://docs.crawl4ai.com/api/arun_many/> |
| [`api-async-webcrawler.md`](./api-async-webcrawler.md) | `docs/md_v2/api/async-webcrawler.md` | <https://docs.crawl4ai.com/api/async-webcrawler/> |
| [`api-c4a-script-reference.md`](./api-c4a-script-reference.md) | `docs/md_v2/api/c4a-script-reference.md` | <https://docs.crawl4ai.com/api/c4a-script-reference/> |
| [`api-crawl-result.md`](./api-crawl-result.md) | `docs/md_v2/api/crawl-result.md` | <https://docs.crawl4ai.com/api/crawl-result/> |
| [`api-digest.md`](./api-digest.md) | `docs/md_v2/api/digest.md` | <https://docs.crawl4ai.com/api/digest/> |
| [`api-parameters.md`](./api-parameters.md) | `docs/md_v2/api/parameters.md` | <https://docs.crawl4ai.com/api/parameters/> |
| [`api-strategies.md`](./api-strategies.md) | `docs/md_v2/api/strategies.md` | <https://docs.crawl4ai.com/api/strategies/> |

## core

| Local file | Upstream | Site |
| --- | --- | --- |
| [`core-adaptive-crawling.md`](./core-adaptive-crawling.md) | `docs/md_v2/core/adaptive-crawling.md` | <https://docs.crawl4ai.com/core/adaptive-crawling/> |
| [`core-browser-crawler-config.md`](./core-browser-crawler-config.md) | `docs/md_v2/core/browser-crawler-config.md` | <https://docs.crawl4ai.com/core/browser-crawler-config/> |
| [`core-c4a-script.md`](./core-c4a-script.md) | `docs/md_v2/core/c4a-script.md` | <https://docs.crawl4ai.com/core/c4a-script/> |
| [`core-cache-modes.md`](./core-cache-modes.md) | `docs/md_v2/core/cache-modes.md` | <https://docs.crawl4ai.com/core/cache-modes/> |
| [`core-cli.md`](./core-cli.md) | `docs/md_v2/core/cli.md` | <https://docs.crawl4ai.com/core/cli/> |
| [`core-content-selection.md`](./core-content-selection.md) | `docs/md_v2/core/content-selection.md` | <https://docs.crawl4ai.com/core/content-selection/> |
| [`core-crawler-result.md`](./core-crawler-result.md) | `docs/md_v2/core/crawler-result.md` | <https://docs.crawl4ai.com/core/crawler-result/> |
| [`core-deep-crawling.md`](./core-deep-crawling.md) | `docs/md_v2/core/deep-crawling.md` | <https://docs.crawl4ai.com/core/deep-crawling/> |
| [`core-domain-mapping.md`](./core-domain-mapping.md) | `docs/md_v2/core/domain-mapping.md` | <https://docs.crawl4ai.com/core/domain-mapping/> |
| [`core-examples.md`](./core-examples.md) | `docs/md_v2/core/examples.md` | <https://docs.crawl4ai.com/core/examples/> |
| [`core-fit-markdown.md`](./core-fit-markdown.md) | `docs/md_v2/core/fit-markdown.md` | <https://docs.crawl4ai.com/core/fit-markdown/> |
| [`core-installation.md`](./core-installation.md) | `docs/md_v2/core/installation.md` | <https://docs.crawl4ai.com/core/installation/> |
| [`core-link-media.md`](./core-link-media.md) | `docs/md_v2/core/link-media.md` | <https://docs.crawl4ai.com/core/link-media/> |
| [`core-local-files.md`](./core-local-files.md) | `docs/md_v2/core/local-files.md` | <https://docs.crawl4ai.com/core/local-files/> |
| [`core-markdown-generation.md`](./core-markdown-generation.md) | `docs/md_v2/core/markdown-generation.md` | <https://docs.crawl4ai.com/core/markdown-generation/> |
| [`core-page-interaction.md`](./core-page-interaction.md) | `docs/md_v2/core/page-interaction.md` | <https://docs.crawl4ai.com/core/page-interaction/> |
| [`core-quickstart.md`](./core-quickstart.md) | `docs/md_v2/core/quickstart.md` | <https://docs.crawl4ai.com/core/quickstart/> |
| [`core-simple-crawling.md`](./core-simple-crawling.md) | `docs/md_v2/core/simple-crawling.md` | <https://docs.crawl4ai.com/core/simple-crawling/> |
| [`core-table_extraction.md`](./core-table_extraction.md) | `docs/md_v2/core/table_extraction.md` | <https://docs.crawl4ai.com/core/table_extraction/> |
| [`core-url-seeding.md`](./core-url-seeding.md) | `docs/md_v2/core/url-seeding.md` | <https://docs.crawl4ai.com/core/url-seeding/> |

## extraction

| Local file | Upstream | Site |
| --- | --- | --- |
| [`extraction-chunking.md`](./extraction-chunking.md) | `docs/md_v2/extraction/chunking.md` | <https://docs.crawl4ai.com/extraction/chunking/> |
| [`extraction-clustring-strategies.md`](./extraction-clustring-strategies.md) | `docs/md_v2/extraction/clustring-strategies.md` | <https://docs.crawl4ai.com/extraction/clustring-strategies/> |
| [`extraction-llm-strategies.md`](./extraction-llm-strategies.md) | `docs/md_v2/extraction/llm-strategies.md` | <https://docs.crawl4ai.com/extraction/llm-strategies/> |
| [`extraction-no-llm-strategies.md`](./extraction-no-llm-strategies.md) | `docs/md_v2/extraction/no-llm-strategies.md` | <https://docs.crawl4ai.com/extraction/no-llm-strategies/> |

## Not carried

| Upstream page | Reason |
| --- | --- |
| `docs/md_v2/CONTRIBUTING.md` | contributor guide for the project, not usage |
| `docs/md_v2/advanced/crawl-dispatcher.md` | pre-release announcement; the dispatchers shipped, see advanced/multi-url-crawling.md |
| `docs/md_v2/apps/c4a-script/README.md` | docs-site apps, not the crawl API |
| `docs/md_v2/apps/crawl4ai-assistant/README.md` | docs-site apps, not the crawl API |
| `docs/md_v2/apps/index.md` | docs-site apps, not the crawl API |
| `docs/md_v2/apps/llmtxt/build.md` | docs-site apps, not the crawl API |
| `docs/md_v2/apps/llmtxt/why.md` | docs-site apps, not the crawl API |
| `docs/md_v2/basic/installation.md` | superseded by core/installation.md |
| `docs/md_v2/blog/articles/adaptive-crawling-revolution.md` | release notes and articles: version history, not the current API |
| `docs/md_v2/blog/articles/dockerize_hooks.md` | release notes and articles: version history, not the current API |
| `docs/md_v2/blog/articles/llm-context-revolution.md` | release notes and articles: version history, not the current API |
| `docs/md_v2/blog/articles/virtual-scroll-revolution.md` | release notes and articles: version history, not the current API |
| `docs/md_v2/blog/index.md` | release notes and articles: version history, not the current API |
| `docs/md_v2/blog/releases/0.4.0.md` | release notes and articles: version history, not the current API |
| `docs/md_v2/blog/releases/0.4.1.md` | release notes and articles: version history, not the current API |
| `docs/md_v2/blog/releases/0.4.2.md` | release notes and articles: version history, not the current API |
| `docs/md_v2/blog/releases/0.5.0.md` | release notes and articles: version history, not the current API |
| `docs/md_v2/blog/releases/0.6.0.md` | release notes and articles: version history, not the current API |
| `docs/md_v2/blog/releases/0.7.0.md` | release notes and articles: version history, not the current API |
| `docs/md_v2/blog/releases/0.7.1.md` | release notes and articles: version history, not the current API |
| `docs/md_v2/blog/releases/0.7.2.md` | release notes and articles: version history, not the current API |
| `docs/md_v2/blog/releases/0.7.3.md` | release notes and articles: version history, not the current API |
| `docs/md_v2/blog/releases/0.7.6.md` | release notes and articles: version history, not the current API |
| `docs/md_v2/blog/releases/v0.4.3b1.md` | release notes and articles: version history, not the current API |
| `docs/md_v2/blog/releases/v0.7.5.md` | release notes and articles: version history, not the current API |
| `docs/md_v2/blog/releases/v0.7.7.md` | release notes and articles: version history, not the current API |
| `docs/md_v2/blog/releases/v0.7.8.md` | release notes and articles: version history, not the current API |
| `docs/md_v2/blog/releases/v0.8.0.md` | release notes and articles: version history, not the current API |
| `docs/md_v2/blog/releases/v0.8.5.md` | release notes and articles: version history, not the current API |
| `docs/md_v2/blog/releases/v0.9.1.md` | release notes and articles: version history, not the current API |
| `docs/md_v2/blog/releases/v0.9.2.md` | release notes and articles: version history, not the current API |
| `docs/md_v2/branding/index.md` | brand guidelines |
| `docs/md_v2/complete-sdk-reference.md` | root-level page: only pages inside a carried section are mirrored |
| `docs/md_v2/core/ask-ai.md` | page hosts only an interactive widget — no prose to mirror |
| `docs/md_v2/core/llmtxt.md` | llmtxt app front end, not the crawl API |
| `docs/md_v2/core/self-hosting.md` | deploying the Crawl4AI server, not using the library |
| `docs/md_v2/index.md` | site landing page |
| `docs/md_v2/marketplace/README.md` | marketplace listing, not the crawl API |
| `docs/md_v2/migration/table_extraction_v073.md` | migration guides for pre-0.9 API shapes |
| `docs/md_v2/migration/webscraping-strategy-migration.md` | migration guides for pre-0.9 API shapes |
| `docs/md_v2/privacy.md` | site legal page |
| `docs/md_v2/stats.md` | site telemetry page |
| `docs/md_v2/support.md` | site support page |
| `docs/md_v2/terms.md` | site legal page |
