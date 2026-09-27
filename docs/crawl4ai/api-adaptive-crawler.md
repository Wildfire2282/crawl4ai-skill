---
source: https://docs.crawl4ai.com/api/adaptive-crawler/
title: "AdaptiveCrawler"
fetched: 2026-09-27
---

# AdaptiveCrawler
The `AdaptiveCrawler` class implements intelligent web crawling that automatically determines when sufficient information has been gathered to answer a query. It uses a three-layer scoring system to evaluate coverage, consistency, and saturation.
## Constructor

```
AdaptiveCrawler(
    crawler: AsyncWebCrawler,
    config: Optional[AdaptiveConfig] = None
)
Copy
```

### Parameters
  * **crawler** (`AsyncWebCrawler`): The underlying web crawler instance to use for fetching pages
  * **config** (`Optional[AdaptiveConfig]`): Configuration settings for adaptive crawling behavior. If not provided, uses default settings.


## Primary Method
### digest()
The main method that performs adaptive crawling starting from a URL with a specific query.

```
async def digest(
    start_url: str,
    query: str,
    resume_from: Optional[Union[str, Path]] = None
) -> CrawlState
Copy
```

#### Parameters
  * **start_url** (`str`): The starting URL for crawling
  * **query** (`str`): The search query that guides the crawling process
  * **resume_from** (`Optional[Union[str, Path]]`): Path to a saved state file to resume from


#### Returns
  * **CrawlState** : The final crawl state containing all crawled URLs, knowledge base, and metrics


#### Example

```
async with AsyncWebCrawler() as crawler:
    adaptive = AdaptiveCrawler(crawler)
    state = await adaptive.digest(
        start_url="https://docs.python.org",
        query="async context managers"
    )
Copy
```

## Properties
### confidence
Current confidence score (0-1) indicating information sufficiency.

```
@property
def confidence(self) -> float
Copy
```

### coverage_stats
Dictionary containing detailed coverage statistics.

```
@property
def coverage_stats(self) -> Dict[str, float]
Copy
```

Returns: - **coverage** : Query term coverage score - **consistency** : Information consistency score
- **saturation** : Content saturation score - **confidence** : Overall confidence score
### is_sufficient
Boolean indicating whether sufficient information has been gathered.

```
@property
def is_sufficient(self) -> bool
Copy
```

### state
Access to the current crawl state.

```
@property
def state(self) -> CrawlState
Copy
```

## Methods
### get_relevant_content()
Retrieve the most relevant content from the knowledge base.

```
def get_relevant_content(
    self,
    top_k: int = 5
) -> List[Dict[str, Any]]
Copy
```

#### Parameters
  * **top_k** (`int`): Number of top relevant documents to return (default: 5)


#### Returns
List of dictionaries containing: - **url** : The URL of the page - **content** : The page content - **score** : Relevance score - **metadata** : Additional page metadata
### print_stats()
Display crawl statistics in formatted output.

```
def print_stats(
    self,
    detailed: bool = False
) -> None
Copy
```

#### Parameters
  * **detailed** (`bool`): If True, shows detailed metrics with colors. If False, shows summary table.


### export_knowledge_base()
Export the collected knowledge base to a JSONL file.

```
def export_knowledge_base(
    self,
    path: Union[str, Path]
) -> None
Copy
```

#### Parameters
  * **path** (`Union[str, Path]`): Output file path for JSONL export


#### Example

```
adaptive.export_knowledge_base("my_knowledge.jsonl")
Copy
```

### import_knowledge_base()
Import a previously exported knowledge base.

```
async def import_knowledge_base(
    self,
    path: Union[str, Path]
) -> None
Copy
```

#### Parameters
  * **path** (`Union[str, Path]`): Path to JSONL file to import


## Configuration
The `AdaptiveConfig` class controls the behavior of adaptive crawling:

```
@dataclass
class AdaptiveConfig:
    confidence_threshold: float = 0.8      # Stop when confidence reaches this
    max_pages: int = 50                    # Maximum pages to crawl
    top_k_links: int = 5                   # Links to follow per page
    min_gain_threshold: float = 0.1        # Minimum expected gain to continue
    save_state: bool = False               # Auto-save crawl state
    state_path: Optional[str] = None       # Path for state persistence
Copy
```

### Example with Custom Config

```
config = AdaptiveConfig(
    confidence_threshold=0.7,
    max_pages=20,
    top_k_links=3
)

adaptive = AdaptiveCrawler(crawler, config=config)
Copy
```

## Complete Example

```
import asyncio
from crawl4ai import AsyncWebCrawler, AdaptiveCrawler, AdaptiveConfig

async def main():
    # Configure adaptive crawling
    config = AdaptiveConfig(
        confidence_threshold=0.75,
        max_pages=15,
        save_state=True,
        state_path="my_crawl.json"
    )

    async with AsyncWebCrawler() as crawler:
        adaptive = AdaptiveCrawler(crawler, config)

        # Start crawling
        state = await adaptive.digest(
            start_url="https://example.com/docs",
            query="authentication oauth2 jwt"
        )

        # Check results
        print(f"Confidence achieved: {adaptive.confidence:.0%}")
        adaptive.print_stats()

        # Get most relevant pages
        for page in adaptive.get_relevant_content(top_k=3):
            print(f"- {page['url']} (score: {page['score']:.2f})")

        # Export for later use
        adaptive.export_knowledge_base("auth_knowledge.jsonl")

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

## See Also
  * [digest() Method Reference](https://docs.crawl4ai.com/api/digest/)
  * [Adaptive Crawling Guide](https://docs.crawl4ai.com/core/adaptive-crawling/)
  * [Advanced Adaptive Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/)
