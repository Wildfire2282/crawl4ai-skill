#!/usr/bin/env python3
"""Mirror the upstream Crawl4AI documentation into docs/crawl4ai/, from the repository.

Source: `unclecode/crawl4ai`, branch `develop`, directory `docs/md_v2`. That directory is what the
docs site is built from — `mkdocs.yml` sets `docs_dir: docs/md_v2`, the only plugin is `search`, and
no page uses a `--8<--` snippet include — so the repository files carry the same prose as the site,
minus the site's HTML→Markdown round trip (which injects the copy-button label into every fenced
block and drops blank lines) and minus the sitemap crawl that used to discover the page set.

`develop` and not `main`: the published site is built from the branch the documentation is written
on. `docs/md_v2/core/installation.md` on the site carries a "Version numbering" section (PEP 440,
`pip install -U crawl4ai`, `--pre`) that exists on develop and not on main, and over the 48 carried
pages develop matches the published site everywhere except one backtick that the site's Markdown
escaping mangles. The branch is a constant here, not a parameter: the pipeline's contract is "what
the published documentation says", and a branch switch is a deliberate edit.

Change detection is incremental and cheap:

    commits?path=docs/md_v2&per_page=1   -> has the documentation moved at all? (one request)
    git/trees/<sha>?recursive=1          -> every page's blob id at that commit (one request)
    raw.githubusercontent.com/<sha>/...  -> bodies of the pages whose blob changed (n requests)

The blob ids are recorded in `_manifest.json`, so a second run downloads nothing. A run whose pages
already agree with the skill's stamps exits 0 without touching the network at all (`--verify`), and
`--check` answers "is there work to do" with a single request — that is the fast path the scheduled
workflow takes on a quiet Monday.

Output: <out>/<section>-<page>.md, flat so every reference stays one level deep, each carrying YAML
front matter (source URL, title, fetch date). Markdown links to sibling pages are rewritten to their
docs.crawl4ai.com URL, because the flat mirror has no sibling directories to resolve `../` against;
every other byte is the upstream file's.

    _INDEX.md       sections, counts, and every upstream page this mirror deliberately does not carry
    _manifest.json  {rel: {path, url, title, blob, sha256, bytes}} — the baseline update_skill.py diffs
    _upstream.json  the commit the files came from, plus the skipped inventory

Usage   : python scripts/sync_docs_repo.py                    # incremental sync
          python scripts/sync_docs_repo.py --check             # fast path: 0 = in sync, 3 = work to do
          python scripts/sync_docs_repo.py --verify            # offline: page bytes, manifest, skill stamps
          python scripts/sync_docs_repo.py --full              # refetch every carried page
          python scripts/sync_docs_repo.py --reindex           # offline: apply the policy to files on disk
          python scripts/sync_docs_repo.py --commit <sha>      # pin a commit instead of the branch tip

Set GITHUB_TOKEN (or GH_TOKEN) to raise the API rate limit from 60 to 5000 requests an hour; the
anonymous limit is enough for the scheduled run's two or three requests.

Exit codes: 0 in sync, 3 work to do (--check/--verify only), 2 unusable input or network failure.
"""

from __future__ import annotations

import argparse
import json
import posixpath
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import Any

REPO = "unclecode/crawl4ai"
BRANCH = "develop"
DOCS_PREFIX = "docs/md_v2/"
SITE = "https://docs.crawl4ai.com"  # the rendered docs; every mirrored page keeps its URL there
INDEX_NAME = "_INDEX.md"
MANIFEST_NAME = "_manifest.json"
UPSTREAM_NAME = "_upstream.json"

# Sections carried into the mirror. A section appears here only if it documents using the crawl API
# rather than the project around it; anything else stays out and shows up under "Not carried" in
# _INDEX.md, so a new upstream section is visible instead of silently ignored.
SECTIONS = ("advanced", "api", "core", "extraction")

# Pages inside a carried section that are still not carried, with the reason. File-level only: the
# section-level reasons are derived from SECTIONS above.
CURATED_OUT: tuple[tuple[str, str], ...] = (
    ("docs/md_v2/advanced/crawl-dispatcher.md",
     "pre-release announcement; the dispatchers shipped, see advanced/multi-url-crawling.md"),
    ("docs/md_v2/core/ask-ai.md",
     "page hosts only an interactive widget — no prose to mirror"),
    ("docs/md_v2/core/llmtxt.md",
     "llmtxt app front end, not the crawl API"),
    ("docs/md_v2/core/self-hosting.md",
     "deploying the Crawl4AI server, not using the library"),
)

# Reason strings for the sections and site-level pages the mirror leaves out. Purely so the index and
# the report say why, in the same voice the curation notes always used.
SECTION_REASONS = {
    "apps": "docs-site apps, not the crawl API",
    "ask_ai": "interactive widget host — no prose to mirror",
    "basic": "superseded by core/installation.md",
    "blog": "release notes and articles: version history, not the current API",
    "branding": "brand guidelines",
    "marketplace": "marketplace listing, not the crawl API",
    "migration": "migration guides for pre-0.9 API shapes",
}
SITE_PAGE_REASONS = {
    "CONTRIBUTING.md": "contributor guide for the project, not usage",
    "index.md": "site landing page",
    "privacy.md": "site legal page",
    "stats.md": "site telemetry page",
    "support.md": "site support page",
    "terms.md": "site legal page",
}
DEFAULT_SECTION_REASON = "outside the documented crawl API — add the section to SECTIONS in scripts/{script} to carry it"
DEFAULT_PAGE_REASON = "root-level page: only pages inside a carried section are mirrored"

# A Markdown link to a sibling page: `[text](../core/x.md#anchor)` and friends. The mirror is flat, so
# the target is re-pointed at its docs.crawl4ai.com URL.
MD_LINK = re.compile(r"\]\((?!https?://|mailto:|#)([^)\s]+?)\.md(#[^)\s]*)?\)")
FRONT_MATTER = re.compile(r"\A---\n(.*?\n)---\n\n?", re.DOTALL)
SCRIPT = Path(__file__).name


class Failure(Exception):
    """Unusable input or a request that cannot be completed."""


def project_root() -> Path:
    """Nearest ancestor that looks like this project: it has a docs/ directory."""
    script_dir = Path(__file__).resolve().parent
    for candidate in (script_dir, *script_dir.parents):
        if (candidate / "docs").is_dir():
            return candidate
    return Path.cwd()


PROJECT = project_root()
DEFAULT_OUT = PROJECT / "docs" / "crawl4ai"
DEFAULT_SKILL = PROJECT / ".agents" / "skills" / "crawl4ai"


# --------------------------------------------------------------------------- GitHub


def api(url: str, attempts: int = 3) -> Any:
    """GET a JSON document from the GitHub API, retrying transient failures with a short backoff."""
    import os

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "crawl4ai-skill-sync",
        **({"Authorization": f"Bearer {token}"} if token else {}),
    }
    last = ""
    for attempt in range(attempts):
        if attempt:
            time.sleep(2 * attempt)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=45) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:  # 404 is final, 403 is usually the anonymous rate limit
            last = f"HTTP {exc.code} from {url}"
            if exc.code == 404:
                break
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = f"{type(exc).__name__}: {exc} for {url}"
    raise Failure(f"{last}; set GITHUB_TOKEN to raise the API rate limit" if "403" in last else last)


def latest_docs_commit(commit: str | None) -> tuple[str, str]:
    """(sha, date) of the commit to mirror: the requested one, else the tip of develop touching docs."""
    if commit:
        data = api(f"https://api.github.com/repos/{REPO}/commits/{commit}")
        return data["sha"], data["commit"]["committer"]["date"][:10]
    url = (f"https://api.github.com/repos/{REPO}/commits?sha={BRANCH}"
           f"&path={DOCS_PREFIX.rstrip('/')}&per_page=1")
    data = api(url)
    if not isinstance(data, list) or not data:
        raise Failure(f"{REPO}:{BRANCH} lists no commit touching {DOCS_PREFIX}")
    return data[0]["sha"], data[0]["commit"]["committer"]["date"][:10]


def upstream_tree(sha: str) -> dict[str, str]:
    """{repo path: blob id} for every .md under docs/md_v2 at this commit, carried or not."""
    data = api(f"https://api.github.com/repos/{REPO}/git/trees/{sha}?recursive=1")
    if not isinstance(data, dict) or "tree" not in data:
        raise Failure(f"{REPO}@{sha[:8]}: unexpected tree response")
    if data.get("truncated"):
        raise Failure(f"{REPO}@{sha[:8]}: the tree listing was truncated; pin the run to a commit")
    return {entry["path"]: entry["sha"] for entry in data["tree"]
            if entry.get("type") == "blob" and entry["path"].startswith(DOCS_PREFIX)
            and entry["path"].endswith(".md")}


def fetch_body(repo_path: str, sha: str) -> str:
    """The Markdown of one upstream page, at the commit that listed it."""
    url = f"https://raw.githubusercontent.com/{REPO}/{sha}/{repo_path}"
    request = urllib.request.Request(url, headers={"User-Agent": "crawl4ai-skill-sync"})
    try:
        with urllib.request.urlopen(request, timeout=45) as resp:
            return resp.read().decode("utf-8")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        raise Failure(f"cannot read {repo_path} at {sha[:8]}: {exc}") from exc


# --------------------------------------------------------------------------- policy and naming


def classify(repo_path: str) -> tuple[bool, str]:
    """(carried, reason) for an upstream page: the one place the curation policy is decided."""
    for path, reason in CURATED_OUT:
        if repo_path == path:
            return False, reason
    rel = repo_path[len(DOCS_PREFIX):]
    section = rel.split("/")[0]
    if "/" not in rel:
        return False, SITE_PAGE_REASONS.get(rel, DEFAULT_PAGE_REASON.format(script=SCRIPT))
    if section not in SECTIONS:
        return False, SECTION_REASONS.get(section, DEFAULT_SECTION_REASON.format(script=SCRIPT))
    return True, ""


def local_name(repo_path: str) -> str:
    """`docs/md_v2/core/page-interaction.md` -> `core-page-interaction.md`; index stays `index.md`."""
    rel = repo_path[len(DOCS_PREFIX):][:-3]
    return f"{rel.replace('/', '-')}.md"


def site_url(repo_path: str) -> str:
    """The page's URL on docs.crawl4ai.com, which is what the skill and the index cite."""
    rel = repo_path[len(DOCS_PREFIX):][:-3]
    return f"{SITE}/{rel}/" if "/" in rel else f"{SITE}/"


def absolutize(body: str, repo_path: str) -> str:
    """Point sibling-page links at the site, since `../` has nothing to resolve against here."""
    base = posixpath.dirname(repo_path[len(DOCS_PREFIX):])

    def replace(match: re.Match) -> str:
        target = posixpath.normpath(posixpath.join(base, match.group(1)))
        if target.startswith(".."):
            return match.group(0)
        return f"]({SITE}/{target}/{match.group(2) or ''})"

    return MD_LINK.sub(replace, body)


def title_of(body: str, repo_path: str) -> str:
    """The page's own H1, else its filename — quoted into the front matter, so quotes are folded."""
    heading = next((line[2:].strip() for line in body.splitlines() if line.startswith("# ")), "")
    return (heading or Path(repo_path).stem.replace("-", " ").title()).replace('"', "'")


def render(repo_path: str, body: str, fetched: str) -> str:
    text = body.rstrip("\n")
    return (f'---\nsource: {site_url(repo_path)}\ntitle: "{title_of(text, repo_path)}"\n'
            f"fetched: {fetched}\n---\n\n{text}\n")


def split_page(text: str) -> tuple[str, str]:
    """(front matter, body) of a mirrored page; a page without front matter is all body."""
    match = FRONT_MATTER.match(text)
    return (match.group(0), text[match.end():]) if match else ("", text)


def read_page(path: Path) -> dict[str, str]:
    """url, title, fetched and body of a file on disk; empty strings when it has no front matter."""
    front, body = split_page(path.read_text(encoding="utf-8", errors="replace"))

    def field(name: str) -> str:
        match = re.search(rf"^{name}:[ \t]*(.*)$", front, re.MULTILINE)
        return match.group(1).strip().strip('"') if match else ""

    return {"source": field("source"), "title": field("title"), "fetched": field("fetched"), "body": body}


def write_text(path: Path, text: str) -> None:
    """Write the bytes this script intends to write, on every platform.

    `Path.write_text` translates "\\n" to os.linesep, so on Windows the same page would land on disk
    as CRLF. The manifest records sha256 over those bytes, which would make a Windows run and a Linux
    run disagree about every page; the mirror hashes the same content wherever it is built.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def read_json(path: Path) -> dict:
    """The JSON document at path, or {} when it is absent, empty or unreadable."""
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def docs_snapshot(manifest: dict) -> str:
    """One hash over the whole mirror, stable under page order and metadata churn.

    The same formula `scripts/update_skill.py` stamps into the skill's `docs-snapshot`, so a mismatch
    between the two is exactly what `--check` reports as work to do.
    """
    digest = sha256()
    for rel in sorted(manifest):
        digest.update(f"{rel} {manifest[rel].get('sha256', '')}\n".encode())
    return digest.hexdigest()


def skill_stamps(skill: Path) -> dict[str, str]:
    """The script-owned `metadata:` values of the skill's SKILL.md."""
    page = skill / "SKILL.md"
    if not page.is_file():
        raise Failure(f"no SKILL.md at {page}")
    front, _ = split_page(page.read_text(encoding="utf-8"))
    return {name: value for name, value in re.findall(r"^  ([a-z-]+):[ \t]*(.*)$", front, re.MULTILINE)}


# --------------------------------------------------------------------------- outputs


def build_index(rows: list[tuple[str, str]], skipped: list[tuple[str, str]], commit: str,
                commit_date: str, synced: str) -> str:
    """Sections of the mirror, then everything upstream deliberately left out, with its reason."""
    groups: dict[str, list[tuple[str, str]]] = {}
    for rel, repo_path in rows:
        groups.setdefault(rel.split("-")[0] if "-" in rel else "(root)", []).append((rel, repo_path))
    refresh = f"python scripts/{SCRIPT}"
    lines = [
        f"# Documentation mirror — {REPO} {DOCS_PREFIX.rstrip('/')}",
        "",
        (f"Mirror of <https://github.com/{REPO}/tree/{BRANCH}/{DOCS_PREFIX.rstrip('/')}>, taken "
         f"{synced} by `scripts/{SCRIPT}` (project tool; independent of any agent skill)."),
        (f"{len(rows)} pages from commit `{commit[:8]}` ({commit_date}); page bodies are the upstream "
         "Markdown, with sibling-page links re-pointed at their docs.crawl4ai.com URL."),
        (f"Pages outside `SECTIONS` in `scripts/{SCRIPT}`, or listed in its `CURATED_OUT`, are not "
         f"carried ({len(skipped)} upstream page(s) excluded by policy) — see below."),
        "Files are flat (`<section>-<page>.md`) so every reference stays one level deep.",
        "",
        "Refresh from the project root:",
        "",
        "```bash",
        refresh,
        f"{refresh} --check     # is there upstream work at all? one request, no download",
        f"{refresh} --reindex   # offline: apply the policy and rebuild this index",
        "```",
        "",
    ]
    for section in sorted(groups):
        lines += [f"## {section}", "", "| Local file | Upstream | Site |", "| --- | --- | --- |"]
        lines += [f"| [`{rel}`](./{rel}) | `{repo_path}` | <{site_url(repo_path)}> |"
                  for rel, repo_path in sorted(groups[section])]
        lines.append("")
    if skipped:
        lines += ["## Not carried", "",
                  "| Upstream page | Reason |", "| --- | --- |"]
        lines += [f"| `{repo_path}` | {reason} |" for repo_path, reason in sorted(skipped)]
        lines.append("")
    return "\n".join(lines)


def write_manifest(path: Path, entries: dict[str, dict]) -> None:
    """{rel: {path, url, title, blob, sha256, bytes}} for every mirror page, sorted by path."""
    document: dict[str, dict] = {}
    for rel in sorted(entries):
        page = path.parent / rel
        document[rel] = {
            "path": entries[rel]["path"],
            "url": site_url(entries[rel]["path"]),
            "title": entries[rel]["title"],
            "blob": entries[rel]["blob"],
            "sha256": sha256(page.read_bytes()).hexdigest() if page.is_file() else "",
            "bytes": page.stat().st_size if page.is_file() else 0,
        }
    write_text(path, json.dumps(document, indent=2, ensure_ascii=False) + "\n")


def prune_stale(keep: set[str], out: Path) -> list[str]:
    """Delete mirrored pages this run did not keep, so a rename or a removal upstream is followed."""
    removed: list[str] = []
    for path in sorted(out.glob("*.md")):
        if path.name in keep or path.name.startswith("_"):
            continue
        if not path.read_text(encoding="utf-8", errors="ignore").startswith("---\nsource:"):
            continue  # not ours — leave it alone
        path.unlink()
        removed.append(path.name)
    return removed


# --------------------------------------------------------------------------- stages


def survey_upstream(sha: str) -> tuple[dict[str, str], dict[str, str]]:
    """(carried {repo path: blob}, skipped {repo path: reason}) at one commit."""
    tree = upstream_tree(sha)
    carried, skipped = {}, {}
    for repo_path, blob in tree.items():
        ok, reason = classify(repo_path)
        (carried.__setitem__(repo_path, blob) if ok else skipped.__setitem__(repo_path, reason))
    return carried, skipped


def sync(out: Path, sha: str, commit_date: str, full: bool, as_json: bool) -> int:
    """Download the pages whose blob id moved and rebuild index, manifest and upstream record."""
    carried, skipped = survey_upstream(sha)
    if not carried:
        raise Failure(f"no carried page under {DOCS_PREFIX} at {sha[:8]}; check SECTIONS and CURATED_OUT")
    previous = read_json(out / MANIFEST_NAME)
    fetched = date.today().isoformat()
    written, fetched_pages, kept, entries = [], [], [], {}
    for repo_path, blob in sorted(carried.items()):
        rel = local_name(repo_path)
        path = out / rel
        known = previous.get(rel) or {}
        # The blob id identifies the upstream content; a page whose blob is unchanged is not
        # downloaded again, and a page whose body is unchanged keeps its file (and its `fetched`
        # date). The manifest's own hash decides whether the file on disk is that page: bytes that no
        # longer hash to what the manifest recorded (a mangled checkout, a hand edit) are fetched
        # again, so a mirror the gate reports as altered is repaired by the sync that follows it
        # instead of being passed through for ever.
        intact = path.is_file() and known.get("sha256") == sha256(path.read_bytes()).hexdigest()
        body = None if not full and known.get("blob") == blob and intact else \
            absolutize(fetch_body(repo_path, sha), repo_path)
        if body is not None:
            fetched_pages.append(rel)
        on_disk = read_page(path) if path.is_file() else None
        title = title_of(body if body is not None else (on_disk or {}).get("body", ""), repo_path)
        if body is not None and (on_disk is None or on_disk["body"].rstrip("\n") != body.rstrip("\n")):
            write_text(path, render(repo_path, body, fetched))
            written.append(rel)
        kept.append(rel)
        entries[rel] = {"path": repo_path, "blob": blob, "title": title}
    removed = prune_stale(set(kept), out)

    # The outputs carry dates ("synced", "taken"), so rebuild them only when something they describe
    # actually moved: a page written or removed, a blob or path that changed, a new upstream commit, or
    # a different set of skipped pages. A `--full` refetch that finds identical bytes therefore leaves
    # the mirror, the index and the record untouched — including their dates.
    state = read_json(out / UPSTREAM_NAME)
    skipped_now = {repo_path: reason for repo_path, reason in sorted(skipped.items())}
    meta = {rel: [entries[rel]["path"], entries[rel]["blob"]] for rel in entries}
    previous_meta = {rel: [entry.get("path", ""), entry.get("blob", "")] for rel, entry in previous.items()}
    unchanged = (not written and not removed and meta == previous_meta
                 and state.get("commit") == sha and state.get("skipped") == skipped_now)
    if not unchanged:
        write_manifest(out / MANIFEST_NAME, entries)
        write_text(out / INDEX_NAME, build_index(
            [(rel, entries[rel]["path"]) for rel in sorted(entries)],
            list(skipped.items()), sha, commit_date, fetched))
        write_text(out / UPSTREAM_NAME, json.dumps({
            "repository": REPO, "branch": BRANCH, "commit": sha, "commit_date": commit_date,
            "synced": fetched, "pages": len(entries), "skipped": skipped_now,
        }, indent=2, ensure_ascii=False) + "\n")
    manifest = read_json(out / MANIFEST_NAME)

    new_sections = sorted({repo_path[len(DOCS_PREFIX):].split("/")[0] for repo_path in skipped
                           if "/" in repo_path[len(DOCS_PREFIX):]}
                          - set(SECTIONS))
    summary = {
        "upstream_commit": sha, "commit_date": commit_date, "pages": len(entries),
        "written": written, "fetched": fetched_pages, "removed": removed, "skipped": len(skipped),
        "skipped_sections": new_sections, "snapshot": docs_snapshot(manifest)[:16],
        "changed": not unchanged, "out": str(out),
    }
    if as_json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(f"docs: {len(entries)} pages at {sha[:8]} ({commit_date}), snapshot "
              f"{summary['snapshot']}, {len(fetched_pages)} fetched, {len(written)} written, "
              f"{len(removed)} removed"
              + ("" if summary["changed"] else " — nothing changed, files left as they were"))
        for name in written:
            print(f"  [written] {name}")
        for name in removed:
            print(f"  [removed] {name}")
        if new_sections:
            print(f"  [note] upstream sections not carried: {', '.join(new_sections)}")
    return 0


def consistency(out: Path, skill: Path) -> tuple[list[str], dict]:
    """Reasons the mirror and the skill are not in sync, plus the values they were judged on.

    Every page the manifest names has to be on disk and to hash to the sha256 the manifest recorded;
    the manifest's hashes are what `.gitattributes` keeps a checkout from rewriting, so this is where
    a mangled or hand-edited page is caught before it reaches a commit.
    """
    state = read_json(out / UPSTREAM_NAME)
    manifest = read_json(out / MANIFEST_NAME)
    stamps = skill_stamps(skill)
    reasons: list[str] = []
    if not manifest:
        reasons.append(f"no readable {MANIFEST_NAME} under {out}")
    if not state.get("commit"):
        reasons.append(f"no readable {UPSTREAM_NAME} under {out}: the docs were never synced")
    if state.get("commit") and stamps.get("docs-commit") != state["commit"]:
        reasons.append(f"the mirror is at {state['commit'][:8]} but the skill is stamped "
                       f"{stamps.get('docs-commit', 'nothing')[:8]}")
    if manifest and stamps.get("docs-snapshot") != docs_snapshot(manifest)[:16]:
        reasons.append(f"the skill's docs-snapshot {stamps.get('docs-snapshot', 'nothing')} does not "
                       f"describe the committed mirror")
    if manifest and stamps.get("docs-pages") != str(len(manifest)):
        reasons.append(f"the mirror holds {len(manifest)} pages, the skill is stamped "
                       f"{stamps.get('docs-pages', 'nothing')}")
    missing, altered = [], []
    for rel, entry in sorted(manifest.items()):
        page = out / rel
        if not page.is_file():
            missing.append(rel)
        elif entry.get("sha256") and sha256(page.read_bytes()).hexdigest() != entry["sha256"]:
            altered.append(rel)
    if missing:
        reasons.append(f"{len(missing)} page(s) named by the manifest are not on disk, e.g. {missing[0]}")
    if altered:
        reasons.append(f"{len(altered)} page(s) on disk do not hash to the manifest, e.g. {altered[0]}: "
                       f"a run of scripts/{SCRIPT} restores the upstream bytes")
    return reasons, {"recorded_commit": state.get("commit", ""), "pages": len(manifest),
                     "missing": len(missing), "altered": len(altered),
                     "skill_commit": stamps.get("docs-commit", ""),
                     "skill_snapshot": stamps.get("docs-snapshot", ""),
                     "snapshot": docs_snapshot(manifest)[:16] if manifest else ""}


def check(out: Path, skill: Path, as_json: bool) -> int:
    """The fast path: one request answers whether anything downstream has work to do."""
    reasons, observed = consistency(out, skill)
    sha, commit_date = latest_docs_commit(None)
    if observed["recorded_commit"] != sha:
        reasons.insert(0, f"upstream {DOCS_PREFIX.rstrip('/')} moved to {sha[:8]} ({commit_date})")
    observed["upstream_commit"] = sha
    observed["up_to_date"] = not reasons
    observed["reasons"] = reasons
    if as_json:
        print(json.dumps(observed, indent=2, ensure_ascii=False))
    else:
        for reason in reasons:
            print(f"[out of sync] {reason}")
        print("Crawl4AI is already synchronized." if not reasons
              else f"{len(reasons)} reason(s) to run the full pipeline")
    return 0 if not reasons else 3


def verify(out: Path, skill: Path, as_json: bool) -> int:
    """Offline twin of --check: mirror, manifest and skill stamps against each other, no network."""
    reasons, observed = consistency(out, skill)
    observed["up_to_date"] = not reasons
    observed["reasons"] = reasons
    if as_json:
        print(json.dumps(observed, indent=2, ensure_ascii=False))
    else:
        for reason in reasons:
            print(f"[out of sync] {reason}")
        print("mirror, manifest and skill agree." if not reasons else f"{len(reasons)} inconsistency(ies)")
    return 0 if not reasons else 3


def reindex(out: Path, as_json: bool) -> int:
    """Offline: apply the current policy and rebuild index, manifest and upstream record.

    The only way to change the curation of a mirror without re-reading upstream. Pages the policy now
    excludes are deleted, pages on disk keep their bytes (and their `fetched` dates).
    """
    entries: dict[str, dict] = {}
    dropped: list[str] = []
    for path in sorted(out.glob("*.md")):
        if path.name.startswith("_"):
            continue
        page = read_page(path)
        source = page["source"]
        if not source.startswith(f"{SITE}/"):
            print(f"[reindex] skipping {path.name}: no source URL in its front matter", file=sys.stderr)
            continue
        rel = source[len(SITE) + 1:].rstrip("/")
        repo_path = f"{DOCS_PREFIX}{rel}.md" if rel else f"{DOCS_PREFIX}index.md"
        carried, reason = classify(repo_path)
        if not carried:
            path.unlink()
            dropped.append(f"{path.name} ({reason})")
            continue
        entries[path.name] = {"path": repo_path, "title": page["title"] or title_of(page["body"], repo_path),
                              "blob": (read_json(out / MANIFEST_NAME).get(path.name) or {}).get("blob", "")}
    if not entries:
        raise Failure(f"the curation policy excludes every page in {out}")
    write_manifest(out / MANIFEST_NAME, entries)
    manifest = read_json(out / MANIFEST_NAME)
    recorded = read_json(out / UPSTREAM_NAME)
    carried, skipped = ({}, {})
    if recorded.get("commit"):
        try:
            carried, skipped = survey_upstream(recorded["commit"])
        except Failure as exc:  # offline: keep the inventory the last sync wrote
            skipped = recorded.get("skipped", {})
            print(f"[reindex] upstream inventory unavailable ({exc}); keeping the recorded one",
                  file=sys.stderr)
    write_text(out / INDEX_NAME, build_index(
        [(rel, entries[rel]["path"]) for rel in sorted(entries)], list(skipped.items()),
        recorded.get("commit", "unknown"), recorded.get("commit_date", "unknown"),
        recorded.get("synced", date.today().isoformat())))
    for line in dropped:
        print(f"[reindex] removed {line}", file=sys.stderr)
    summary = {"pages": len(entries), "removed": dropped, "snapshot": docs_snapshot(manifest)[:16]}
    if as_json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(f"[reindex] {len(entries)} pages indexed, {len(dropped)} removed -> {out}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Mirror unclecode/crawl4ai's docs/md_v2 into docs/crawl4ai (standalone; no skill required).",
        epilog="Exit codes:\n"
               "  0  synced (or, with --check/--verify, nothing to do)\n"
               "  3  --check/--verify only: upstream or the skill moved, run the pipeline\n"
               "  2  unusable input, or the GitHub API could not be read\n"
               "\nExamples:\n"
               "  python scripts/sync_docs_repo.py            # incremental sync\n"
               "  python scripts/sync_docs_repo.py --check    # one request: is there work?\n"
               "  python scripts/sync_docs_repo.py --verify   # offline: mirror vs manifest vs skill\n"
               "  python scripts/sync_docs_repo.py --full     # refetch every carried page\n"
               "  python scripts/sync_docs_repo.py --reindex  # offline: apply the curation policy\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="mirror directory (default: docs/crawl4ai)")
    parser.add_argument("--skill", default=str(DEFAULT_SKILL), help="skill directory whose stamps are checked")
    parser.add_argument("--commit", help=f"upstream commit to mirror (default: the tip of {BRANCH} touching docs/md_v2)")
    parser.add_argument("--check", action="store_true", help="one request: exit 0 in sync, 3 work to do")
    parser.add_argument("--verify", action="store_true", help="offline consistency: page bytes, manifest, stamps")
    parser.add_argument("--full", action="store_true", help="refetch every carried page, ignoring the manifest")
    parser.add_argument("--reindex", action="store_true", help="offline: apply the policy, rebuild index and manifest")
    parser.add_argument("--json", action="store_true", help="machine-readable summary on stdout")
    args = parser.parse_args()

    out, skill = Path(args.out).resolve(), Path(args.skill).resolve()
    try:
        if args.reindex:
            return reindex(out, args.json)
        if args.check:
            return check(out, skill, args.json)
        if args.verify:
            return verify(out, skill, args.json)
        if not out.is_dir():
            raise Failure(f"{out} does not exist; create it or pass --out")
        sha, commit_date = latest_docs_commit(args.commit)
        return sync(out, sha, commit_date, args.full, args.json)
    except Failure as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
