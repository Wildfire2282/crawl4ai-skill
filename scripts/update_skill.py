#!/usr/bin/env python3
"""Keep the crawl4ai skill in step with the upstream docs mirror and the installed package.

Stages, in order:
  1. Snapshot — hash the docs mirror and diff it against a baseline (`git show HEAD:...` or --baseline).
  2. Coverage — union the API names the skill's prose cites into the generated regions of
                `.agents/skills/crawl4ai/scripts/check_api.py`, so the gate keeps checking them.
  3. Gates    — run `check_api.py` (names, parameters, result fields, documented defaults) and
                `.style_check.py`. A red gate stops the run and nothing is stamped.
  4. Stamp    — with the gates green, write `api-tracked`, `docs-snapshot`, `docs-pages` and
                `docs-synced` into the SKILL.md front matter, plus the `Targets crawl4ai X.Y.x`
                line in `compatibility:`.
  5. Probes   — with --probe, re-observe the values the references quote (live crawl, network).
  6. Report   — `reports/skill-sync.md`: upstream changes mapped onto the skill files that cite
                them, gate results, probe deltas and the actions left for a maintainer or an agent.
  7. Agent    — with --agent-cmd, hand the report to an agent CLI and re-run the gates.

The prose in SKILL.md and references/ stays hand-written: its `[verified: run]` markers are claims
about executed crawls, which no unattended job can assert. This tool regenerates everything that is
derivable and reports the rest as an action list.

Exit codes: 0 in sync with green gates, 1 drift or a failed gate, 2 unusable input.
"""

from __future__ import annotations

import argparse
import ast
import asyncio
import hashlib
import importlib
import inspect
import json
import re
import shlex
import subprocess
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

PROJECT = Path(__file__).resolve().parent.parent
DOCS = PROJECT / "docs" / "crawl4ai"
SKILL = PROJECT / ".agents" / "skills" / "crawl4ai"
REPORT = PROJECT / "reports" / "skill-sync.md"
MANIFEST = "_manifest.json"
CANDIDATE_MODULES = (
    "crawl4ai",
    "crawl4ai.deep_crawling",
    "crawl4ai.deep_crawling.filters",
    "crawl4ai.deep_crawling.scorers",
    "crawl4ai.chunking_strategy",
    "crawl4ai.processors.pdf",
    "crawl4ai.async_crawler_strategy",
)
REGION = "# --- generated: {name} (scripts/update_skill.py unions the curated list with cited names) ---"
TOKEN = re.compile(r"`([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?)`")
REJECTED_FLAGS = ("bypass_cache", "disable_cache", "no_cache_read", "no_cache_write")
PROBES = (
    ("example.com default crawl: raw_markdown length", 166),
    ('example.com css_selector="main": raw_markdown length', 1),
    ("news.ycombinator.com JsonCss tr.athing record count", 30),
)


class Failure(Exception):
    """Unusable input or a stage that cannot continue."""


def run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def split_command(text: str) -> list[str]:
    """Split an agent command line; POSIX shlex would mangle Windows separators in paths."""
    tokens = shlex.split(text, posix=sys.platform != "win32")
    return [t[1:-1] if len(t) > 1 and t[0] == t[-1] and t[0] in "\"'" else t for t in tokens]


def load_manifest(path: Path) -> dict[str, dict]:
    if not path.is_file():
        raise Failure(f"no docs manifest at {path} — run scripts/mirror_docs_site.py first")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise Failure(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict) or not data:
        raise Failure(f"{path} lists no pages")
    return data


def docs_snapshot(manifest: dict[str, dict]) -> str:
    """One hash over the whole mirror, stable under page order and metadata churn."""
    digest = hashlib.sha256()
    for rel in sorted(manifest):
        digest.update(f"{rel} {manifest[rel].get('sha256', '')}\n".encode())
    return digest.hexdigest()


def baseline_manifest(explicit: Path | None, docs_dir: Path) -> tuple[dict[str, dict] | None, str]:
    """The manifest the skill was last synced against, plus where it came from."""
    if explicit is not None:
        if not explicit.is_file():
            raise Failure(f"no baseline manifest at {explicit}")
        return load_manifest(explicit), str(explicit)
    try:
        rel = docs_dir.relative_to(PROJECT).as_posix()
    except ValueError:
        rel = docs_dir.name
    code, out = run(["git", "show", f"HEAD:{rel}/{MANIFEST}"], cwd=PROJECT)
    if code != 0:
        return None, "none (git has no committed manifest yet)"
    try:
        return json.loads(out), f"git HEAD:{rel}/{MANIFEST}"
    except json.JSONDecodeError:
        return None, "none (committed manifest is not valid JSON)"


def docs_diff(previous: dict[str, dict] | None, current: dict[str, dict]) -> dict[str, list[str]]:
    """Added / removed / changed page names, by content hash."""
    if previous is None:
        return {"added": [], "removed": [], "changed": []}
    return {
        "added": sorted(set(current) - set(previous)),
        "removed": sorted(set(previous) - set(current)),
        "changed": sorted(name for name in set(current) & set(previous)
                          if current[name].get("sha256") != previous[name].get("sha256")),
    }


def skill_markdown(skill_dir: Path) -> dict[str, str]:
    """Every prose file of the skill, keyed by its path relative to the skill directory."""
    files = [skill_dir / "SKILL.md", *sorted((skill_dir / "references").glob("*.md"))]
    return {path.relative_to(skill_dir).as_posix(): path.read_text(encoding="utf-8") for path in files if path.is_file()}


def cited_by(skill_dir: Path, needles: list[str]) -> list[str]:
    """`file:line` of every skill line citing an upstream page, matched on URL path or local name."""
    hits: list[str] = []
    wanted = [needle for needle in needles if len(needle) > 4]
    if not wanted:
        return hits
    for rel, text in skill_markdown(skill_dir).items():
        for number, line in enumerate(text.splitlines(), 1):
            if any(needle in line for needle in wanted):
                hits.append(f"{rel}:{number}")
    return hits


def needles_for(local_name: str, url: str) -> list[str]:
    """Two ways a skill file can cite a mirrored page: its upstream path and its local name."""
    stem = local_name.removesuffix(".md")
    return [urlparse(url).path, stem]


def topic_match(page_text: str, skill_dir: Path) -> tuple[str, float] | None:
    """Skill file that shares the most distinctive vocabulary with an upstream page.

    The skill cites the API rather than the docs, so a citation is an exact signal and this is the
    fallback: the file whose wording overlaps the changed page most, as a lead for the refresh.
    """
    words = re.compile(r"[a-zA-Z][a-zA-Z0-9_]{5,}")
    page = set(words.findall(page_text.lower()))
    if not page:
        return None
    best: tuple[str, float] | None = None
    for rel, text in skill_markdown(skill_dir).items():
        overlap = len(page & set(words.findall(text.lower()))) / len(page)
        if overlap and (best is None or overlap > best[1]):
            best = (rel, overlap)
    return best if best and best[1] >= 0.15 else None


def coverage_names(text: str) -> set[str]:
    """Attribute names already covered by the generated regions."""
    names: set[str] = set()
    for region in ("imports", "run_params", "browser_params", "methods", "result_fields"):
        for item in read_region(text, region):
            names.add(item[1] if isinstance(item, tuple) else item)
    return names


def derived_coverage(skill_dir: Path, covered: set[str]) -> dict[str, list]:
    """Names the skill's prose cites, resolved against the installed package.

    Deliberately narrow: import candidates have to look like names (UpperCamelCase or CONSTANT),
    resolve to a non-module attribute, and add something the regions do not already check. Generic
    lowercase words (`config`, `url`) and the rejected legacy flags stay out.
    """
    import crawl4ai

    rejected = set(REJECTED_FLAGS)
    modules = {}
    for name in CANDIDATE_MODULES:
        try:
            modules[name] = importlib.import_module(name)
        except ImportError:
            continue
    run_params = set(inspect.signature(crawl4ai.CrawlerRunConfig).parameters)
    browser_params = set(inspect.signature(crawl4ai.BrowserConfig).parameters)
    result_fields = set(getattr(crawl4ai.CrawlResult, "model_fields", {}))

    text = "\n".join(skill_markdown(skill_dir).values())
    tokens = {token for token in TOKEN.findall(text)}
    plain = {token for token in tokens if "." not in token}
    dotted = {token for token in tokens if "." in token}

    imports: list[tuple[str, str]] = []
    for token in sorted(plain):
        looks_like_a_name = bool(re.match(r"^[A-Z][A-Za-z0-9]*$|^[A-Z][A-Z0-9_]+$", token))
        if not looks_like_a_name or token in covered:
            continue
        for module_name, module in modules.items():
            holder = getattr(module, token, None)
            if holder is not None and not inspect.ismodule(holder):
                imports.append((module_name, token))
                break
    methods: list[tuple[str, str, str]] = []
    for token in sorted(dotted):
        holder_name, _, attribute = token.partition(".")
        if attribute.startswith("_"):
            continue
        for module_name, module in modules.items():
            holder = getattr(module, holder_name, None)
            if inspect.isclass(holder) and hasattr(holder, attribute) and attribute not in covered:
                methods.append((module_name, holder_name, attribute))
                break
    return {
        "imports": imports,
        "run_params": sorted(token for token in plain
                             if len(token) >= 5 and token in run_params
                             and token not in covered and token not in rejected),
        "browser_params": sorted(token for token in plain
                                 if len(token) >= 5 and token in browser_params
                                 and token not in covered and token not in rejected),
        "methods": methods,
        "result_fields": sorted(token for token in plain if token in result_fields and token not in covered),
    }


def read_region(text: str, name: str) -> list:
    """Items of a generated list, parsed so multi-item lines cannot hide duplicates."""
    marker = REGION.format(name=name)
    start = text.find(marker)
    if start < 0:
        raise Failure(f"check_api.py has no generated region for {name!r}")
    body_start = text.index("[", start) + 1
    body_end = text.index("\n]", body_start)
    return list(ast.literal_eval("[" + text[body_start:body_end] + "]"))


def write_region(text: str, name: str, items: list) -> str:
    """Replace a generated list body, one item per line, curated order first."""
    marker = REGION.format(name=name)
    start = text.find(marker)
    body_start = text.index("[", start) + 1
    body_end = text.index("\n]", body_start)
    rendered = "".join(f"    {render_item(item)},\n" for item in items)
    return text[:body_start] + "\n" + rendered + text[body_end:]


def render_item(value) -> str:
    if isinstance(value, tuple):
        return "(" + ", ".join(json.dumps(part) for part in value) + ")"
    return json.dumps(value)


def sync_coverage(skill_dir: Path, check_api_text: str, derived: dict, write: bool) -> tuple[str, list[str]]:
    """Union the cited names into the generated regions; returns the new text and what changed."""
    changes: list[str] = []
    text = check_api_text
    regions = {
        "imports": derived["imports"],
        "run_params": derived["run_params"],
        "browser_params": derived["browser_params"],
        "methods": derived["methods"],
        "result_fields": derived["result_fields"],
    }
    for name, extra in regions.items():
        existing = read_region(text, name)
        merged = list(existing)
        for item in extra:
            if item not in merged:
                merged.append(item)
                changes.append(f"{name}: + {render_item(item)}")
        if merged != existing:
            text = write_region(text, name, merged)
    if changes and write:
        (skill_dir / "scripts" / "check_api.py").write_text(text, encoding="utf-8")
    return text, changes


def read_front_matter(text: str) -> tuple[str, str]:
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise Failure("SKILL.md has no front matter block")
    return parts[0] + "---" + parts[1] + "---", parts[2]


def stamp_front_matter(text: str, values: dict[str, str]) -> tuple[str, list[str]]:
    """Set `metadata:` keys and the compatibility target line; returns the text and what changed."""
    head, body = read_front_matter(text)
    changes: list[str] = []
    for key, value in values.items():
        pattern = re.compile(rf"^(  {key}:).*$", re.M)
        found = pattern.search(head)
        if found:
            if found.group(0) != f"  {key}: {value}":
                changes.append(f"metadata.{key}: {value}")
            head = pattern.sub(f"  {key}: {value}", head, count=1)
            continue
        block = re.search(r"^metadata:\n((?:  \S.*\n)*)", head, re.M)
        if not block:
            raise Failure("SKILL.md has no metadata: block to stamp")
        insert_at = block.end()
        head = head[:insert_at] + f"  {key}: {value}\n" + head[insert_at:]
        changes.append(f"metadata.{key}: {value} (added)")
    target = values.get("api-tracked", "")
    minor = ".".join(target.split(".")[:2]) + ".x" if target else ""
    if minor:
        new_head, count = re.subn(r"Targets crawl4ai \d+\.\d+\.x", f"Targets crawl4ai {minor}", head)
        if count and new_head != head:
            changes.append(f"compatibility: Targets crawl4ai {minor}")
        head = new_head
    return head + body, changes


def gate_results(project: Path, skill_dir: Path) -> list[tuple[str, int, str]]:
    """The gates a published skill has to pass: API drift and project style."""
    results = []
    for label, cmd in (
        ("check_api.py", [sys.executable, "-B", str(skill_dir / "scripts" / "check_api.py")]),
        (".style_check.py", [sys.executable, "-B", str(project / ".style_check.py")]),
    ):
        code, out = run(cmd, cwd=project)
        results.append((label, code, out))
        if code != 0:
            break
    return results


def probes() -> list[tuple[str, object, object]]:
    """Live re-observation of the values the references quote. Network and browsers required."""
    from crawl4ai import (AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig,
                          JsonCssExtractionStrategy)

    schema = {"name": "Front page items", "baseSelector": "tr.athing",
              "fields": [{"name": "title", "selector": "span.titleline > a", "type": "text"},
                         {"name": "url", "selector": "span.titleline > a", "type": "attribute",
                          "attribute": "href"}]}

    async def main() -> list[tuple[str, object, object]]:
        observed: list[tuple[str, object, object]] = []
        async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as crawler:
            plain = await crawler.arun("https://example.com", config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS))
            observed.append((PROBES[0][0], PROBES[0][1], len(plain.markdown.raw_markdown)))
            selected = await crawler.arun(
                "https://example.com",
                config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS, css_selector="main"))
            observed.append((PROBES[1][0], PROBES[1][1], len(selected.markdown.raw_markdown)))
            listed = await crawler.arun("https://news.ycombinator.com", config=CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS, extraction_strategy=JsonCssExtractionStrategy(schema)))
            rows = json.loads(listed.extracted_content or "[]")
            observed.append((PROBES[2][0], PROBES[2][1], len(rows)))
        return observed

    return asyncio.run(main())


def current_version() -> str:
    import importlib.metadata as metadata

    try:
        return metadata.version("crawl4ai")
    except metadata.PackageNotFoundError as exc:
        raise Failure("crawl4ai is not importable; install it before running the pipeline") from exc


def build_report(state: dict) -> str:
    diff = state["diff"]
    lines = [
        "# Skill sync report",
        "",
        f"- generated: {state['today']}",
        f"- crawl4ai: {state['version']} (skill expects {state['expected']}: "
        f"{'match' if state['version_ok'] else 'MISMATCH'})",
        f"- docs mirror: {len(state['manifest'])} pages, snapshot `{state['snapshot'][:12]}`",
        f"- baseline: {state['baseline_source']}",
        f"- result: {'in sync' if state['ok'] else 'ACTION REQUIRED'}",
        "",
        "## Upstream docs changes",
        "",
    ]
    if state["baseline_source"].startswith("none"):
        lines += ["No committed baseline to diff against: this run only records the current snapshot.", ""]
    else:
        for kind in ("added", "changed", "removed"):
            names = diff[kind]
            lines.append(f"### {kind} ({len(names)})")
            lines.append("")
            if not names:
                lines += ["None.", ""]
                continue
            for name in names:
                url = (state["manifest"].get(name) or state["previous"].get(name, {})).get("url", "")
                cited = state["cited"].get(name, [])
                lead = state["leads"].get(name)
                where = f"cited by {', '.join(cited[:3])}" if cited else "NOT cited by any skill file"
                if lead:
                    where += f"; closest section {lead[0]} (overlap {lead[1]:.2f})"
                lines.append(f"- `{name}` — <{url}> — {where}")
            lines.append("")
    lines += ["## Gates", ""]
    for label, code, out in state["gates"]:
        lines.append(f"- {label}: exit {code}")
        for line in out.splitlines()[:12]:
            lines.append(f"  - {line}")
    lines.append("")
    if state["coverage"]:
        lines += ["## Coverage merged into check_api.py", ""]
        lines += [f"- {change}" for change in state["coverage"]]
        lines.append("")
    if state["probes"]:
        lines += ["## Probes (live)", "", "| claim | documented | observed |", "| --- | --- | --- |"]
        for claim, documented, observed in state["probes"]:
            mark = "" if documented == observed else " **CHANGED**"
            lines.append(f"| {claim} | {documented} | {observed}{mark} |")
        lines.append("")
    elif state.get("probe_error"):
        lines += ["## Probes (live)", "", f"Unavailable this run: `{state['probe_error']}`.", ""]
    lines += ["## Actions", ""]
    lines += [f"- [ ] {action}" for action in state["actions"]] or ["- [ ] none"]
    lines.append("")
    return "\n".join(lines)


def actions_for(state: dict) -> list[str]:
    actions: list[str] = []
    if not state["version_ok"]:
        actions.append(f"crawl4ai {state['version']} is installed but the skill targets {state['expected']}: "
                       "re-read the changed APIs and update references/API.md, then re-run this pipeline")
    for name in state["diff"]["added"]:
        if not state["cited"].get(name):
            actions.append(f"decide whether `{name}` belongs in the skill (routing row, recipe) or in CURATED_OUT")
    for kind in ("changed", "removed"):
        for name in state["diff"][kind]:
            cited = state["cited"].get(name)
            if cited:
                actions.append(f"re-read `{name}` (upstream {kind}) and refresh {', '.join(cited[:3])}")
    for label, code, _ in state["gates"]:
        if code != 0:
            actions.append(f"fix the {label} failure listed above; nothing was stamped")
    for claim, documented, observed in state["probes"]:
        if documented != observed:
            actions.append(f"re-observe `{claim}` in the references (documented {documented}, observed {observed})")
    if state.get("probe_error"):
        actions.append(f"probes did not run ({state['probe_error']}); re-run with network and browsers before merging")
    if state["pending_coverage"]:
        actions.append("re-run this pipeline with write access so the merged coverage is persisted")
    return actions


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync the crawl4ai skill with the docs mirror and the installed package.",
        epilog="Exit codes:\n"
        "  0  in sync, gates green\n"
        "  1  drift or a failed gate (reports/skill-sync.md lists the actions)\n"
        "  2  unusable input (missing mirror, manifest or skill)\n"
        "\nExamples:\n"
        "  python scripts/update_skill.py                       # write stamps and merge coverage\n"
        "  python scripts/update_skill.py --check-only          # gate a pull request, write nothing\n"
        "  python scripts/update_skill.py --probe               # add live re-observation\n"
        "  python scripts/update_skill.py --agent-cmd 'omp -p --no-session'\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--docs", default=str(DOCS), help=f"docs mirror directory (default: {DOCS})")
    parser.add_argument("--skill", default=str(SKILL), help=f"skill directory (default: {SKILL})")
    parser.add_argument("--baseline", help="manifest to diff against (default: the committed one)")
    parser.add_argument("--report", default=str(REPORT), help=f"report path (default: {REPORT})")
    parser.add_argument("--probe", action="store_true", help="re-observe the quoted values with a live crawl")
    parser.add_argument("--agent-cmd", default="", help="agent CLI prefix for the prose pass; the report path is appended")
    parser.add_argument("--check-only", action="store_true", help="verify without writing anything")
    parser.add_argument("--json", action="store_true", help="machine-readable summary on stdout")
    args = parser.parse_args()

    docs_dir, skill_dir = Path(args.docs).resolve(), Path(args.skill).resolve()
    report_path = Path(args.report).resolve()
    check_api_path = skill_dir / "scripts" / "check_api.py"
    if not (docs_dir / MANIFEST).is_file():
        print(f"error: no docs manifest in {docs_dir}", file=sys.stderr)
        return 2
    if not (skill_dir / "SKILL.md").is_file() or not check_api_path.is_file():
        print(f"error: {skill_dir} is not a skill directory", file=sys.stderr)
        return 2
    write = not args.check_only

    try:
        manifest = load_manifest(docs_dir / MANIFEST)
        previous, baseline_source = baseline_manifest(Path(args.baseline) if args.baseline else None, docs_dir)
        snapshot = docs_snapshot(manifest)
        version = current_version()
    except Failure as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    diff = docs_diff(previous, manifest)
    changed_names = diff["added"] + diff["changed"] + diff["removed"]
    cited = {
        name: cited_by(skill_dir, needles_for(name, (manifest.get(name) or previous.get(name, {})).get("url", "")))
        for name in changed_names
    }
    leads = {}
    for name in changed_names:
        page = docs_dir / name
        if page.is_file():
            match = topic_match(page.read_text(encoding="utf-8", errors="replace"), skill_dir)
            if match:
                leads[name] = match

    check_api_text = check_api_path.read_text(encoding="utf-8")
    _, coverage = sync_coverage(skill_dir, check_api_text, derived_coverage(skill_dir, coverage_names(check_api_text)), write)

    gates = gate_results(PROJECT, skill_dir)
    gates_green = all(code == 0 for _, code, _ in gates)
    expected_match = re.search(r'"expected":\s*"([^"]+)"', check_api_text)
    expected = expected_match.group(1) if expected_match else "unknown"
    today = date.today().isoformat()

    stamps: list[str] = []
    if gates_green and write:
        skill_text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        stamped, stamps = stamp_front_matter(skill_text, {
            "api-tracked": version,
            "docs-snapshot": snapshot[:16],
            "docs-pages": str(len(manifest)),
            "docs-synced": today,
        })
        if stamped != skill_text:
            (skill_dir / "SKILL.md").write_text(stamped, encoding="utf-8")

    observed: list[tuple[str, object, object]] = []
    probe_error = ""
    if args.probe:
        try:
            observed = probes()
        except Exception as exc:  # noqa: BLE001  (network or browser failure must not kill the run)
            probe_error = f"{type(exc).__name__}: {exc}"
            print(f"[probe] unavailable: {probe_error}", file=sys.stderr)
    state = {
        "today": today, "version": version, "expected": expected,
        "version_ok": expected == "unknown" or version.split(".")[:2] == expected.split(".")[:2],
        "manifest": manifest, "previous": previous or {}, "snapshot": snapshot,
        "baseline_source": baseline_source, "diff": diff, "cited": cited, "stamps": stamps, "leads": leads,
        "gates": gates, "coverage": coverage, "probes": observed, "ok": True, "probe_error": probe_error,
        "pending_coverage": bool(coverage) and not write,
    }
    state["actions"] = actions_for(state)
    state["ok"] = not state["actions"]

    if write:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(build_report(state), encoding="utf-8")

    if args.agent_cmd:
        prompt = (f"Skill sync report at {report_path}. Read it, then update the crawl4ai skill under "
                  f"{skill_dir} to follow it: regenerate the affected references from the upstream docs in "
                  f"{docs_dir} and from the installed crawl4ai package, keep the evidence markers honest, and "
                  f"finish by running python {check_api_path}.")
        code, out = run([*split_command(args.agent_cmd), prompt], cwd=PROJECT)
        print(f"[agent] exit {code}", file=sys.stderr)
        if out:
            print(out[-2000:], file=sys.stderr)
        if code == 0:
            gates = gate_results(PROJECT, skill_dir)
            state["gates"] = gates

    if args.json:
        print(json.dumps({
            "version": version, "docs_pages": len(manifest), "snapshot": snapshot[:16],
            "baseline": baseline_source, "diff": {k: len(v) for k, v in diff.items()},
            "gates": {label: code for label, code, _ in gates}, "coverage_changes": len(coverage),
            "actions": state["actions"], "report": str(report_path) if write else None,
        }, indent=2))
    else:
        print(f"docs: {len(manifest)} pages, snapshot {snapshot[:12]}, baseline {baseline_source}")
        print(f"docs diff: {', '.join(f'{k}={len(v)}' for k, v in diff.items())}")
        for label, code, out in gates:
            print(f"gate {label}: exit {code}")
        for change in coverage:
            print(f"coverage {change}")
        for claim, documented, observed in observed:
            print(f"probe {claim}: documented {documented}, observed {observed}")
        for action in state["actions"]:
            print(f"action {action}")
        if write:
            print(f"report {report_path}")
    return 0 if state["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
