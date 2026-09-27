#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "crawl4ai>=0.9,<1",
#   "httpx>=0.27",
# ]
# ///
"""Walk a documentation site and dump every page to Markdown.

Discovery: the site's sitemap.xml when it has one (exact URL set, one cheap request; a sitemap
index is followed one level down). Otherwise a bounded breadth-first walk of same-domain links,
capped by --max-pages and --depth.

Extraction: each page is rendered to Markdown by crawl4ai, body taken from --selector (default
"main", which MkDocs Material, Docusaurus and GitBook wrap their content in). If that selector
matches nothing on a sample page of the site, whole pages are kept instead of empty files.

Curation: pages listed in CURATED_OUT (below) are never fetched or written — release notes,
migration guides, site/legal pages and superseded snapshots. --reindex applies the current policy
to files already on disk and rebuilds the index without touching the network.

Output: <out>/<section>-<page>.md, flat so every file stays one level deep, each carrying YAML
front matter (source URL, title, fetch date), plus _INDEX.md (grouped by section) and
_manifest.json (`{rel: {url, title, sha256, bytes}}` — the baseline `scripts/update_skill.py`
diffs upstream changes against).

Usage   : python scripts/mirror_docs_site.py --root https://docs.example.com
          python scripts/mirror_docs_site.py --root https://docs.example.com --out docs/example
          python scripts/mirror_docs_site.py --out docs/example --reindex        # offline, applies CURATED_OUT
          python scripts/mirror_docs_site.py --root https://docs.example.com --json
          uv run scripts/mirror_docs_site.py --root https://docs.example.com   # isolated env (PEP 723)

A 400-page site needs no tuning beyond --concurrency (default 4): sessions are memory-adaptive and
rate-limited with backoff. Exits 1 if any page failed, 2 if no page was found.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

import httpx
from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CacheMode,
    CrawlerRunConfig,
    MemoryAdaptiveDispatcher,
    RateLimiter,
)
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.deep_crawling.filters import ContentTypeFilter, DomainFilter, FilterChain

SCRIPT_DIR = Path(__file__).resolve().parent
INDEX_NAME = "_INDEX.md"  # prefixed so it cannot collide with a mirrored site root (index.md)
MANIFEST_NAME = "_manifest.json"
DEFAULT_SELECTOR = "main"  # MkDocs Material, Docusaurus and GitBook wrap the page body in <main>
MIN_BODY = 200  # a selector matching nothing leaves ~1 char of Markdown, with success=True
SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

# Pages this mirror deliberately does not carry. Matched on the URL path: "/section/" excludes the
# section and its children, "/page/" excludes exactly that page, "/" excludes the site root.
# Reasons are kept here so a reader of the mirror can see why a page is missing.
CURATED_OUT: tuple[tuple[str, str], ...] = (
    ("/blog/", "release notes and articles: version history, not the current API"),
    ("/migration/", "migration guides for pre-0.9 API shapes"),
    ("/apps/", "docs-site apps, not the crawl API"),
    ("/core/llmtxt/", "llmtxt app front end, not the crawl API"),
    ("/core/ask-ai/", "page hosts only an interactive widget — no prose to mirror"),
    ("/complete-sdk-reference/", "generated 0.7.4 snapshot (2025-10-19); superseded by api/ and core/"),
    ("/basic/installation/", "superseded by core/installation/"),
    ("/core/self-hosting/", "deploying the Crawl4AI server, not using the library"),
    ("/advanced/crawl-dispatcher/", "pre-release announcement; the dispatchers shipped, see advanced/multi-url-crawling/"),
    ("/CONTRIBUTING/", "contributor guide for the project, not usage"),
    ("/privacy/", "site legal page"),
    ("/terms/", "site legal page"),
    ("/support/", "site support page"),
    ("/stats/", "site telemetry page"),
    ("/branding/", "brand guidelines"),
    ("/", "site landing page"),
)


def curated_out(url: str) -> str | None:
    """Reason this URL is deliberately excluded from the mirror, or None when it is wanted."""
    path = urlparse(url).path
    for pattern, reason in CURATED_OUT:
        if pattern == "/":
            if not path.strip("/"):
                return reason
            continue
        base = pattern.rstrip("/")
        if path.rstrip("/") == base or path.startswith(base + "/"):
            return reason
    return None
_WS = re.compile(r"[ \t]+\n")

Row = tuple[str, str | None, str, str]  # url, markdown | None on failure, title | error, html if stub


def project_root() -> Path:
    """Nearest ancestor that looks like a project root: a git repo, else a directory that has docs/."""
    parents = (SCRIPT_DIR, *SCRIPT_DIR.parents)
    for candidate in parents:
        if (candidate / ".git").exists():
            return candidate
    for candidate in parents:
        if (candidate / "docs").is_dir():
            return candidate
    return Path.cwd()


def out_arg(out: Path) -> str:
    """Render --out the way a reader would type it: relative to the project root when it lives there."""
    try:
        return out.relative_to(project_root()).as_posix()
    except ValueError:
        return out.as_posix()


def local_path(url: str) -> Path:
    """Map a docs URL onto a flat `section-page.md` name.

    Flat names keep the corpus one level deep and stable regardless of what consumes it, so the
    upstream URL path is collapsed with "-" instead of mirroring directories.
    """
    parts = [p for p in urlparse(url).path.strip("/").split("/") if p]
    return Path("-".join(parts) + ".md") if parts else Path("index.md")


def _page_urls(xml: ElementTree.Element, depth: int) -> list[str]:
    """Page URLs in one sitemap document; a <sitemapindex> is followed one level down."""
    if xml.tag.endswith("sitemapindex") and depth == 0:
        found: list[str] = []
        for loc in xml.findall(".//sm:loc", SITEMAP_NS):
            found += _fetch_sitemap((loc.text or "").strip(), depth + 1)
        return found
    return [(loc.text or "").strip() for loc in xml.findall(".//sm:loc", SITEMAP_NS)]


def _fetch_sitemap(url: str, depth: int = 0) -> list[str]:
    resp = httpx.get(url, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    return _page_urls(ElementTree.fromstring(resp.text), depth)


def sitemap_urls(root: str) -> list[str]:
    """Page URLs listed by the site's sitemap, or [] when the site has none to offer."""
    url = root.rstrip("/") + "/sitemap.xml"
    try:
        urls = _fetch_sitemap(url)
    except (httpx.HTTPError, ElementTree.ParseError) as exc:
        print(f"[walk] no usable sitemap at {url} ({exc}) — walking links instead", file=sys.stderr)
        return []
    # Directory listings are pages; asset/attachment URLs are not what "dump each page" means.
    return sorted({u for u in urls if u.endswith("/") or "." not in u.rsplit("/", 1)[-1]})


def run_config(selector: str | None, strategy=None) -> CrawlerRunConfig:
    return CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        css_selector=selector,
        word_count_threshold=1,
        exclude_external_links=True,
        deep_crawl_strategy=strategy,
        stream=strategy is not None,  # a deep crawl yields results as they complete
        verbose=False,
    )


def record(result) -> Row:
    if not result.success:
        return result.url, None, result.error_message or "unknown error", ""
    markdown = result.markdown.raw_markdown if result.markdown else ""
    title = (result.metadata or {}).get("title", "")
    return result.url, markdown, title, result.html if len(markdown.strip()) < MIN_BODY else ""


async def _aiter(outcome):
    """arun_many returns either a list of results or an async generator, depending on version."""
    if hasattr(outcome, "__aiter__"):
        async for item in outcome:
            yield item
    else:
        for item in outcome:
            yield item


async def resolve_selector(crawler: AsyncWebCrawler, page: str, selector: str | None) -> str | None:
    """Drop the body selector when it matches nothing: a non-matching css_selector reports success=True
    and returns an empty page, so probe one page and fall back to whole-page Markdown."""
    if not selector:
        return None
    probe = await crawler.arun(page, config=run_config(selector))
    selected = len((probe.markdown.raw_markdown or "").strip()) if probe.success else 0
    if selected >= MIN_BODY:
        return selector
    whole = await crawler.arun(page, config=run_config(None))
    whole_body = len((whole.markdown.raw_markdown or "").strip()) if whole.success else 0
    if whole_body >= max(MIN_BODY // 4, 2 * selected):
        print(
            f"[walk] css_selector={selector!r} matches nothing on {page} — keeping whole pages",
            file=sys.stderr,
        )
        return None
    return selector


async def crawl_known(
    crawler: AsyncWebCrawler, urls: list[str], selector: str | None, concurrency: int
) -> list[Row]:
    """Fetch a known URL list in parallel, bounded by memory and by a rate limiter with backoff."""
    dispatcher = MemoryAdaptiveDispatcher(
        max_session_permit=concurrency,
        memory_threshold_percent=90.0,
        rate_limiter=RateLimiter(base_delay=(1.0, 3.0), max_retries=3),
    )
    outcome = await crawler.arun_many(urls, config=run_config(selector), dispatcher=dispatcher)
    rows: list[Row] = []
    async for result in _aiter(outcome):
        rows.append(record(result))
        print(f"[walk] {len(rows)}/{len(urls)} pages", end="\r", file=sys.stderr, flush=True)
    print(file=sys.stderr)
    return rows


async def crawl_deep(
    crawler: AsyncWebCrawler, root: str, selector: str | None, max_pages: int, depth: int
) -> list[Row]:
    """Walk same-domain links breadth-first when there is no sitemap to enumerate the pages."""
    strategy = BFSDeepCrawlStrategy(
        max_depth=depth,
        include_external=False,
        max_pages=max_pages,  # mandatory: a deep crawl is unbounded without it
        filter_chain=FilterChain(
            [
                DomainFilter(allowed_domains=[urlparse(root).netloc]),
                ContentTypeFilter(allowed_types=["text/html"]),
            ]
        ),
    )
    rows: list[Row] = []
    async for result in await crawler.arun(root, config=run_config(selector, strategy)):
        rows.append(record(result))
        print(f"[walk] {len(rows)}/{max_pages} pages", end="\r", file=sys.stderr, flush=True)
    print(file=sys.stderr)
    return rows


def probe_target(root: str, urls: list[str]) -> str:
    """Probe a representative content page — the deepest URL the sitemap lists — rather than the root,
    which on some sites is a splash page carrying almost no text of its own."""
    return max(urls, key=lambda u: (urlparse(u).path.count("/"), len(u))) if urls else root


async def walk(
    root: str, selector: str | None, concurrency: int, max_pages: int, depth: int
) -> tuple[list[Row], str | None, list[tuple[str, str]]]:
    urls = sitemap_urls(root)
    curated = [(u, curated_out(u)) for u in urls if curated_out(u)]
    urls = [u for u in urls if not curated_out(u)]
    if urls:
        print(f"[walk] {len(urls)} URLs from sitemap ({len(curated)} curated out)", file=sys.stderr)
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        selector = await resolve_selector(crawler, probe_target(root, urls), selector)
        if urls:
            return await crawl_known(crawler, urls, selector, concurrency), selector, curated
        print(f"[walk] walking links from {root} (max {max_pages} pages, depth {depth})", file=sys.stderr)
        rows = await crawl_deep(crawler, root, selector, max_pages, depth)
        curated = [(r[0], curated_out(r[0])) for r in rows if curated_out(r[0])]
        return [r for r in rows if not curated_out(r[0])], selector, curated


def render(url: str, title: str, markdown: str, fetched: str, note: str = "") -> tuple[str, str]:
    body = _WS.sub("\n", markdown).strip()
    if note and len(body) < MIN_BODY // 10:
        body = ""
    heading = next((ln.lstrip("# ").strip() for ln in body.splitlines() if ln.startswith("# ")), "")
    safe_title = (heading or title or url).replace('"', "'")
    suffix = f"\n\n{note}" if note else ""
    text = f'---\nsource: {url}\ntitle: "{safe_title}"\nfetched: {fetched}\n---\n\n{body}{suffix}\n'
    return text, safe_title


def stub_note(url: str, html: str) -> str:
    """Pages that host an interactive iframe app instead of prose carry no extractable text."""
    if not html or "<iframe" not in html:
        return ""
    match = re.search(r'<iframe[^>]*\bsrc="([^"]+)"', html)
    target = f" (embedded app: {urljoin(url, match.group(1))})" if match else ""
    return f"> No prose on this page — it only hosts an interactive widget{target}."


def prune_stale(keep: set[Path], root: Path) -> list[str]:
    """Delete previously mirrored .md files that this run did not produce (keeps the dir in sync)."""
    removed: list[str] = []
    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root)
        if rel in keep or path.name.startswith("_"):
            continue  # "_INDEX.md" / "_manifest.json" are generated too, but never stale
        head = path.read_text(encoding="utf-8", errors="ignore")[:200]
        if "source:" not in head or "fetched:" not in head:
            continue  # not generated by this script — leave it alone
        path.unlink()
        removed.append(rel.as_posix())
    for path in sorted(root.rglob("*"), reverse=True):
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()
    return removed


def build_index(
    rows: list[tuple[str, str, str]], fetched: str, total: int | None, root: str, out: Path, curation_note: str
) -> str:
    """Group the flat files by their upstream docs section, so a reader can see what a group holds."""
    groups: dict[str, list[tuple[str, str]]] = {}
    for rel, url, _title in rows:
        section = rel.split("-")[0] if "-" in rel else "(root)"
        groups.setdefault(section, []).append((rel, url))
    refresh = f"python scripts/{Path(__file__).name} --root {root.rstrip('/')} --out {out_arg(out)}"
    count = (
        f"{len(rows)}/{total} pages downloaded; page bodies are verbatim Markdown from the live site."
        if total is not None
        else f"{len(rows)} pages; page bodies are verbatim Markdown from the live site."
    )
    lines = [
        f"# Documentation mirror — {urlparse(root).netloc}",
        "",
        f"Standalone mirror of <{root.rstrip('/')}>, taken {fetched} by `scripts/{Path(__file__).name}`"
        " (project tool; independent of any agent skill).",
        count,
        f"Non-core and superseded pages are curated out by `CURATED_OUT` in `scripts/{Path(__file__).name}`"
        f" ({curation_note}).",
        "Files are flat (`<section>-<page>.md`) so every reference stays one level deep.",
        "",
        "Refresh from the project root:",
        "",
        "```bash",
        refresh,
        f"{refresh} --reindex   # offline: apply the curation policy and rebuild this index",
        "```",
        "",
    ]
    for section in sorted(groups):
        lines += [f"## {section}", "", "| Local file | Source |", "| --- | --- |"]
        lines += [f"| [`{rel}`](./{rel}) | <{url}> |" for rel, url in sorted(groups[section])]
        lines.append("")
    return "\n".join(lines)


def read_front_matter(path: Path) -> tuple[str, str, str]:
    """(source url, title, fetched date) of a mirrored page; empty strings when absent."""
    parts = path.read_text(encoding="utf-8", errors="replace").split("---", 2)

    def field(name: str, block: str) -> str:
        match = re.search(rf"^{name}:[ \t]*(.*)$", block, re.M)
        return match.group(1).strip().strip('"') if match else ""

    block = parts[1] if len(parts) > 2 else ""
    return field("source", block), field("title", block), field("fetched", block)


def page_digest(path: Path) -> str:
    """sha256 of a mirrored page — the manifest baseline `scripts/update_skill.py` diffs against."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_text(path: Path, text: str) -> None:
    """Write the bytes this script intends to write, on every platform.

    `Path.write_text` translates "\\n" to os.linesep, so on Windows the same page lands on disk as
    CRLF. The manifest records sha256 over those bytes, which would make a Windows run and a Linux run
    disagree about all 48 pages; a mirror must hash the same content wherever it is built.
    """
    path.write_text(text, encoding="utf-8", newline="\n")


def write_manifest(path: Path, rows: list[tuple[str, str, str]]) -> None:
    """{rel: {url, title, sha256, bytes}} for every mirrored page, sorted by path."""
    manifest = {}
    for rel, url, title in sorted(rows):
        page = path.parent / rel
        manifest[rel] = {"url": url, "title": title, "sha256": page_digest(page), "bytes": page.stat().st_size}
    write_text(path, json.dumps(manifest, indent=2) + "\n")


def reindex(out: Path, root: str | None) -> int:
    """Apply CURATED_OUT to the files already on disk and rebuild the index and manifest.

    Offline by design: the only way to change the curation of a mirror without re-crawling the site.
    """
    pages = sorted(p for p in out.glob("*.md") if not p.name.startswith("_"))
    if not pages:
        print(f"Error: no mirrored pages in {out}", file=sys.stderr)
        return 2
    index_rows: list[tuple[str, str, str]] = []
    removed: list[str] = []
    fetched = date.today().isoformat()
    for path in pages:
        source, title, page_fetched = read_front_matter(path)
        if not source:
            print(f"[reindex] skipping {path.name}: no source URL in its front matter", file=sys.stderr)
            continue
        reason = curated_out(source)
        if reason:
            path.unlink()
            removed.append(f"{path.name} ({reason})")
            continue
        fetched = page_fetched or fetched
        index_rows.append((path.name, source, title or path.stem))
    if not index_rows:
        print("Error: the curation policy excludes every page in this directory", file=sys.stderr)
        return 2
    index_rows.sort()
    resolved_root = root.rstrip("/") + "/" if root else f"{urlparse(index_rows[0][1]).scheme}://{urlparse(index_rows[0][1]).netloc}/"
    write_text(
        out / INDEX_NAME,
        build_index(index_rows, fetched, None, resolved_root, out,
                    f"offline reindex, {len(removed)} file(s) removed"
                    if removed else "offline reindex, mirror already matches the policy"),
    )
    write_manifest(out / MANIFEST_NAME, index_rows)
    for line in removed:
        print(f"[reindex] removed {line}", file=sys.stderr)
    print(f"[reindex] {len(index_rows)} pages indexed, {len(removed)} removed -> {out}", file=sys.stderr)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Walk a documentation site and dump every page to Markdown (standalone; no skill required).",
        epilog="Examples:\n"
        "  python scripts/mirror_docs_site.py --root https://docs.example.com\n"
        "  python scripts/mirror_docs_site.py --root https://docs.example.com --concurrency 8 --json\n"
        "  python scripts/mirror_docs_site.py --root https://docs.example.com --out docs/example\n"
        "  python scripts/mirror_docs_site.py --out docs/example --reindex   # offline curation pass\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--root", help="docs site root, e.g. https://docs.example.com")
    parser.add_argument("--out", help="directory for the mirrored pages (default: docs/<host>)")
    parser.add_argument(
        "--reindex",
        action="store_true",
        help="write no pages: apply CURATED_OUT to the directory on disk and rebuild the index and manifest",
    )
    parser.add_argument(
        "--selector",
        default=DEFAULT_SELECTOR,
        help=f"CSS selector for the page body; pass '' to keep the whole page (default: {DEFAULT_SELECTOR})",
    )
    parser.add_argument("--concurrency", type=int, default=4, help="parallel browser sessions (default: 4)")
    parser.add_argument(
        "--max-pages", type=int, default=500, help="cap for the link walk used when there is no sitemap (default: 500)"
    )
    parser.add_argument("--depth", type=int, default=3, help="link depth for that walk (default: 3)")
    parser.add_argument("--json", action="store_true", help="emit a machine-readable summary on stdout")
    args = parser.parse_args()

    if args.reindex and not args.out:
        parser.error("--reindex needs --out: the directory to re-index")
    if not args.reindex and not args.root:
        parser.error("--root is required unless --reindex is given")
    if args.reindex:
        return reindex(Path(args.out).expanduser().resolve(), args.root)

    root = args.root.rstrip("/") + "/"
    out = Path(args.out).expanduser().resolve() if args.out else project_root() / "docs" / urlparse(root).netloc

    rows, selector, curated = asyncio.run(
        walk(root, args.selector or None, args.concurrency, args.max_pages, args.depth)
    )
    if not rows:
        print(f"Error: no pages found on {root}", file=sys.stderr)
        return 2

    fetched = date.today().isoformat()
    out.mkdir(parents=True, exist_ok=True)
    index_rows: list[tuple[str, str, str]] = []  # local path, url, title
    failures: list[tuple[str, str]] = []
    written: dict[str, str] = {}  # lowercased local path -> url, guard against case-insensitive overwrites
    for url, markdown, extra, html in rows:
        rel = local_path(url)
        key = rel.as_posix().lower()
        if key in written:
            print(f"[walk] duplicate for {rel}: {written[key]} and {url} — keeping the first", file=sys.stderr)
            continue
        written[key] = url
        if markdown is None:
            failures.append((url, extra))
            existing = out / rel
            if existing.exists():  # a transient failure must not drop a page the mirror already carries
                source, title, _ = read_front_matter(existing)
                index_rows.append((rel.as_posix(), source or url, title or rel.stem))
                print(f"[walk] keeping the previous copy of {rel}", file=sys.stderr)
            continue
        note = stub_note(url, html) if html else ""
        text, title = render(url, extra, markdown, fetched, note)
        write_text(out / rel, text)
        index_rows.append((rel.as_posix(), url, title))
        print(f"[ok]   {rel.as_posix():<48} {len(markdown):>7} chars  {title}", file=sys.stderr)

    index_rows.sort()
    removed = prune_stale({Path(rel) for rel, _, _ in index_rows}, out)
    write_text(
        out / INDEX_NAME,
        build_index(index_rows, fetched, len(rows), root, out,
                    f"{len(curated)} upstream page(s) excluded by policy"),
    )
    write_manifest(out / MANIFEST_NAME, index_rows)

    if args.json:
        print(
            json.dumps(
                {
                    "root": root,
                    "fetched": fetched,
                    "selector": selector,
                    "pages": len(rows),
                    "ok": len(index_rows),
                    "failed": len(failures),
                    "removed": removed,
                    "curated": [{"url": u, "reason": r} for u, r in curated],
                    "index": (out / INDEX_NAME).as_posix(),
                    "failures": [{"url": u, "error": e} for u, e in failures],
                    "out": out.as_posix(),
                },
                indent=2,
            )
        )
    elif removed:
        print(f"[walk] pruned {len(removed)} stale file(s): {', '.join(removed[:5])}{' ...' if len(removed) > 5 else ''}", file=sys.stderr)
    if failures:
        print(f"[walk] {len(failures)} FAILED:", file=sys.stderr)
        for url, err in failures:
            print(f"  {url}: {err}", file=sys.stderr)
        return 1
    if not args.json:
        print(f"[walk] complete: {len(index_rows)} pages -> {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
