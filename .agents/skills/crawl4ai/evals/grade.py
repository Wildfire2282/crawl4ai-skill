#!/usr/bin/env python3
"""Grade the mechanical assertions in `evals.json` against a directory of produced output.

Purpose: check that the output-eval assertions discriminate — they pass on a real run and fail
on empty or malformed output. Offline and mechanical: no crawling, no model calls. A case whose
assertions are answered by reading the answer rather than the files is reported as ungraded.

Usage:
    python evals/grade.py <output-dir>            # text report
    python evals/grade.py <output-dir> --json     # JSON report

The directory holds what the eval prompts produced. If it contains `out/`, that subdirectory is
graded; otherwise the directory itself is. Both cases share one directory, matching the recorded
runs, which put `example.md`, `quickstart.md` and `items.json` side by side.

Exit codes: 0 = every assertion passed, 1 = at least one failed, 2 = invalid input.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVALS_PATH = HERE / "evals.json"


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _load_items(root: Path):
    path = root / "items.json"
    if not path.exists():
        return None
    try:
        return json.loads(_read(path))
    except json.JSONDecodeError:
        return None


def grade(root: Path) -> list[tuple[int, int, bool, str]]:
    """Return (eval id, assertion index, passed, evidence) for every assertion in `evals.json`."""
    md = sorted(root.glob("*.md")) if root.is_dir() else []
    items = _load_items(root)
    is_list = isinstance(items, list)
    sizes = ", ".join(f"{p.name}={len(_read(p))}" for p in md) or "no .md files"
    return [
        (1, 0, len(md) >= 2, sizes),
        (1, 1, bool(md) and all(len(_read(p)) > 120 for p in md), sizes),
        (1, 2, any("Example Domain" in _read(p) for p in md), "searched every .md"),
        (1, 3, len(md) >= 2 and all("Brand Book" not in _read(p) for p in md), "searched every .md"),
        (2, 0, is_list, f"items.json -> {type(items).__name__}"),
        (2, 1, is_list and len(items) >= 20, f"{len(items) if is_list else 0} element(s)"),
        (2, 2, is_list and all(isinstance(i, dict) and i.get("title") and i.get("url") for i in items),
         "every element needs non-empty title and url"),
        (2, 3, is_list and all(str(i.get("url", "")).startswith("http") for i in items),
         "every url must start with http"),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Grade the evals.json assertions against a directory of produced output.",
        epilog="Exit codes:\n"
        "  0  every assertion passed\n"
        "  1  at least one assertion failed\n"
        "  2  invalid input (missing directory or evals.json)\n"
        "\nExamples:\n"
        "  python evals/grade.py ../crawl4ai-run/with_skill\n"
        "  python evals/grade.py ../crawl4ai-run/with_skill --json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("output_dir", help="directory holding the produced files (or its parent, if it has out/)")
    parser.add_argument("--json", action="store_true", help="emit the report as JSON on stdout")
    args = parser.parse_args()

    if not EVALS_PATH.exists():
        print(f"error: {EVALS_PATH} not found", file=sys.stderr)
        return 2
    if not Path(args.output_dir).is_dir():
        print(f"error: not a directory: {args.output_dir}", file=sys.stderr)
        return 2

    root = Path(args.output_dir)
    if (root / "out").is_dir():
        root = root / "out"

    cases = json.loads(EVALS_PATH.read_text(encoding="utf-8"))["evals"]
    assertions = {case["id"]: case["assertions"] for case in cases}
    rows = []
    for eval_id, index, passed, evidence in grade(root):
        try:
            text = assertions[eval_id][index]
        except (KeyError, IndexError):
            print(f"error: evals.json has no assertion {eval_id}.{index + 1}; grader and spec have drifted",
                  file=sys.stderr)
            return 2
        rows.append({"eval": eval_id, "assertion": index + 1, "text": text, "passed": passed, "evidence": evidence})

    # A case whose assertions cannot be answered from files (an explanation, a corrected call) is
    # graded by reading the answer, not here: it is reported so a spec that grew a case the grader
    # cannot see is visible, while the pass rate stays the mechanical one.
    graded = {row["eval"] for row in rows}
    ungraded = [{"eval": case["id"], "assertions": len(case["assertions"])}
                for case in cases if case["id"] not in graded]
    failures = [r for r in rows if not r["passed"]]
    if args.json:
        print(json.dumps({"root": str(root), "results": rows, "passed": len(rows) - len(failures),
                          "total": len(rows), "ungraded": ungraded}, indent=2))
    else:
        print(f"root={root}")
        for r in rows:
            print(f"  {'PASS' if r['passed'] else 'FAIL'}  {r['eval']}.{r['assertion']} {r['text']}")
            print(f"        evidence: {r['evidence']}")
        if ungraded:
            print("not graded here (no file-level assertion): "
                  + ", ".join(f"eval {c['eval']} ({c['assertions']} assertion(s))" for c in ungraded))
        print(f"pass rate: {len(rows) - len(failures)}/{len(rows)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
