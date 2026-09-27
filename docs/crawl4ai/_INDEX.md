# Documentation mirror — docs.crawl4ai.com

Standalone mirror of <https://docs.crawl4ai.com>, taken 2026-09-27 by `scripts/mirror_docs_site.py` (project tool; independent of any agent skill).
48/48 pages downloaded; page bodies are verbatim Markdown from the live site.
Non-core and superseded pages are curated out by `CURATED_OUT` in `scripts/mirror_docs_site.py` (41 upstream page(s) excluded by policy).
Files are flat (`<section>-<page>.md`) so every reference stays one level deep.

Refresh from the project root:

```bash
python scripts/mirror_docs_site.py --root https://docs.crawl4ai.com --out docs/crawl4ai
python scripts/mirror_docs_site.py --root https://docs.crawl4ai.com --out docs/crawl4ai --reindex   # offline: apply the curation policy and rebuild this index
```

## advanced

| Local file | Source |
| --- | --- |
| [`advanced-adaptive-strategies.md`](./advanced-adaptive-strategies.md) | <https://docs.crawl4ai.com/advanced/adaptive-strategies/> |
| [`advanced-advanced-features.md`](./advanced-advanced-features.md) | <https://docs.crawl4ai.com/advanced/advanced-features/> |
| [`advanced-anti-bot-and-fallback.md`](./advanced-anti-bot-and-fallback.md) | <https://docs.crawl4ai.com/advanced/anti-bot-and-fallback/> |
| [`advanced-file-downloading.md`](./advanced-file-downloading.md) | <https://docs.crawl4ai.com/advanced/file-downloading/> |
| [`advanced-hooks-auth.md`](./advanced-hooks-auth.md) | <https://docs.crawl4ai.com/advanced/hooks-auth/> |
| [`advanced-identity-based-crawling.md`](./advanced-identity-based-crawling.md) | <https://docs.crawl4ai.com/advanced/identity-based-crawling/> |
| [`advanced-lazy-loading.md`](./advanced-lazy-loading.md) | <https://docs.crawl4ai.com/advanced/lazy-loading/> |
| [`advanced-multi-url-crawling.md`](./advanced-multi-url-crawling.md) | <https://docs.crawl4ai.com/advanced/multi-url-crawling/> |
| [`advanced-network-console-capture.md`](./advanced-network-console-capture.md) | <https://docs.crawl4ai.com/advanced/network-console-capture/> |
| [`advanced-pdf-parsing.md`](./advanced-pdf-parsing.md) | <https://docs.crawl4ai.com/advanced/pdf-parsing/> |
| [`advanced-proxy-security.md`](./advanced-proxy-security.md) | <https://docs.crawl4ai.com/advanced/proxy-security/> |
| [`advanced-session-management.md`](./advanced-session-management.md) | <https://docs.crawl4ai.com/advanced/session-management/> |
| [`advanced-ssl-certificate.md`](./advanced-ssl-certificate.md) | <https://docs.crawl4ai.com/advanced/ssl-certificate/> |
| [`advanced-undetected-browser.md`](./advanced-undetected-browser.md) | <https://docs.crawl4ai.com/advanced/undetected-browser/> |
| [`advanced-virtual-scroll.md`](./advanced-virtual-scroll.md) | <https://docs.crawl4ai.com/advanced/virtual-scroll/> |

## api

| Local file | Source |
| --- | --- |
| [`api-adaptive-crawler.md`](./api-adaptive-crawler.md) | <https://docs.crawl4ai.com/api/adaptive-crawler/> |
| [`api-arun.md`](./api-arun.md) | <https://docs.crawl4ai.com/api/arun/> |
| [`api-arun_many.md`](./api-arun_many.md) | <https://docs.crawl4ai.com/api/arun_many/> |
| [`api-async-webcrawler.md`](./api-async-webcrawler.md) | <https://docs.crawl4ai.com/api/async-webcrawler/> |
| [`api-c4a-script-reference.md`](./api-c4a-script-reference.md) | <https://docs.crawl4ai.com/api/c4a-script-reference/> |
| [`api-crawl-result.md`](./api-crawl-result.md) | <https://docs.crawl4ai.com/api/crawl-result/> |
| [`api-digest.md`](./api-digest.md) | <https://docs.crawl4ai.com/api/digest/> |
| [`api-parameters.md`](./api-parameters.md) | <https://docs.crawl4ai.com/api/parameters/> |
| [`api-strategies.md`](./api-strategies.md) | <https://docs.crawl4ai.com/api/strategies/> |

## core

| Local file | Source |
| --- | --- |
| [`core-adaptive-crawling.md`](./core-adaptive-crawling.md) | <https://docs.crawl4ai.com/core/adaptive-crawling/> |
| [`core-browser-crawler-config.md`](./core-browser-crawler-config.md) | <https://docs.crawl4ai.com/core/browser-crawler-config/> |
| [`core-c4a-script.md`](./core-c4a-script.md) | <https://docs.crawl4ai.com/core/c4a-script/> |
| [`core-cache-modes.md`](./core-cache-modes.md) | <https://docs.crawl4ai.com/core/cache-modes/> |
| [`core-cli.md`](./core-cli.md) | <https://docs.crawl4ai.com/core/cli/> |
| [`core-content-selection.md`](./core-content-selection.md) | <https://docs.crawl4ai.com/core/content-selection/> |
| [`core-crawler-result.md`](./core-crawler-result.md) | <https://docs.crawl4ai.com/core/crawler-result/> |
| [`core-deep-crawling.md`](./core-deep-crawling.md) | <https://docs.crawl4ai.com/core/deep-crawling/> |
| [`core-domain-mapping.md`](./core-domain-mapping.md) | <https://docs.crawl4ai.com/core/domain-mapping/> |
| [`core-examples.md`](./core-examples.md) | <https://docs.crawl4ai.com/core/examples/> |
| [`core-fit-markdown.md`](./core-fit-markdown.md) | <https://docs.crawl4ai.com/core/fit-markdown/> |
| [`core-installation.md`](./core-installation.md) | <https://docs.crawl4ai.com/core/installation/> |
| [`core-link-media.md`](./core-link-media.md) | <https://docs.crawl4ai.com/core/link-media/> |
| [`core-local-files.md`](./core-local-files.md) | <https://docs.crawl4ai.com/core/local-files/> |
| [`core-markdown-generation.md`](./core-markdown-generation.md) | <https://docs.crawl4ai.com/core/markdown-generation/> |
| [`core-page-interaction.md`](./core-page-interaction.md) | <https://docs.crawl4ai.com/core/page-interaction/> |
| [`core-quickstart.md`](./core-quickstart.md) | <https://docs.crawl4ai.com/core/quickstart/> |
| [`core-simple-crawling.md`](./core-simple-crawling.md) | <https://docs.crawl4ai.com/core/simple-crawling/> |
| [`core-table_extraction.md`](./core-table_extraction.md) | <https://docs.crawl4ai.com/core/table_extraction/> |
| [`core-url-seeding.md`](./core-url-seeding.md) | <https://docs.crawl4ai.com/core/url-seeding/> |

## extraction

| Local file | Source |
| --- | --- |
| [`extraction-chunking.md`](./extraction-chunking.md) | <https://docs.crawl4ai.com/extraction/chunking/> |
| [`extraction-clustring-strategies.md`](./extraction-clustring-strategies.md) | <https://docs.crawl4ai.com/extraction/clustring-strategies/> |
| [`extraction-llm-strategies.md`](./extraction-llm-strategies.md) | <https://docs.crawl4ai.com/extraction/llm-strategies/> |
| [`extraction-no-llm-strategies.md`](./extraction-no-llm-strategies.md) | <https://docs.crawl4ai.com/extraction/no-llm-strategies/> |
