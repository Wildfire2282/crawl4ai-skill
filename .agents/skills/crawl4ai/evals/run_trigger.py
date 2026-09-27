#!/usr/bin/env python3
"""Run the trigger evaluation in `trigger_queries.json` against an agent CLI.

Purpose: measure whether this skill activates on queries that should trigger it and stays
dormant on near-miss queries. Ships with the Agent Skills trigger-eval procedure
(three runs per query, trigger rate >= 0.5 required).

Detection (mechanical):
  skill_read — the agent issued a `read` whose result is this skill's body.
  markers    — the final assistant message contains a Crawl4AI-specific API identifier.
  triggered  — skill_read or markers.
A run that times out or writes no transcript is reported as skipped and excluded from the rate;
a query with no completed run is reported as a failure rather than a silent pass.

Usage:
    python evals/run_trigger.py                            # all queries, 1 run each
    python evals/run_trigger.py --runs 3 --split train     # per the evaluation procedure
    python evals/run_trigger.py --agent-cmd "claude -p --output-format json"
    python evals/run_trigger.py --json

Exit codes: 0 = every query met the threshold, 1 = at least one query failed, 2 = invalid input.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
API_MARKERS = re.compile(
    r"AsyncWebCrawler|CrawlerRunConfig|JsonCssExtractionStrategy|JsonXPathExtractionStrategy|"
    r"LLMExtractionStrategy|arun_many|CacheMode|crwl|BrowserConfig"
)
SKILL_BODY = re.compile(r"name:\s*crawl4ai")
THRESHOLD = 0.5


def split_command(text: str) -> list[str]:
    """Split an agent command line, keeping Windows path separators intact.

    POSIX-mode `shlex` treats `\\` as an escape, so `C:\\...\\python.exe` arrives mangled and
    `subprocess` raises FileNotFoundError. Non-POSIX mode keeps the backslashes but retains the
    surrounding quotes, which this strips.
    """
    tokens = shlex.split(text, posix=os.name != "nt")
    return [t[1:-1] if len(t) > 1 and t[0] == t[-1] and t[0] in "\"'" else t for t in tokens]



def parse_transcript(raw: str) -> tuple[bool, str]:
    """Return (skill_body_read, final_assistant_text) from a newline-delimited JSON transcript."""
    skill_read = False
    texts: list[str] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "tool_execution_end" and event.get("toolName") == "read":
            if SKILL_BODY.search(json.dumps(event.get("result", {}))):
                skill_read = True
        if event.get("type") == "message_end" and event.get("message", {}).get("role") == "assistant":
            texts += [p["text"] for p in event["message"].get("content", []) if p.get("type") == "text"]
    return skill_read, (texts[-1] if texts else "")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the trigger evaluation for this skill against an agent CLI.",
        epilog="Exit codes:\n"
        "  0  every query met the threshold\n"
        "  1  at least one query failed the threshold\n"
        "  2  invalid input (missing queries file, unreadable transcript)\n"
        "\nExamples:\n"
        "  python evals/run_trigger.py\n"
        "  python evals/run_trigger.py --runs 3 --split train\n"
        "  python evals/run_trigger.py --json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--queries", default=str(HERE / "trigger_queries.json"),
                        help="queries JSON file (default: trigger_queries.json beside this script)")
    parser.add_argument("--agent-cmd", default="omp -p --no-session --mode=json",
                        help="agent CLI prefix; the query is appended as the final argument")
    parser.add_argument("--runs", type=int, default=1, help="runs per query, at least 1 (default: 1; the procedure recommends 3)")
    parser.add_argument("--split", choices=("train", "validation", "all"), default="all",
                        help="subset to run (default: all)")
    parser.add_argument("--threshold", type=float, default=THRESHOLD,
                        help=f"trigger-rate threshold for a PASS (default: {THRESHOLD})")
    parser.add_argument("--timeout", type=int, default=300, help="per-run timeout in seconds")
    parser.add_argument("--json", action="store_true", help="emit results as JSON on stdout")
    args = parser.parse_args()
    if args.runs < 1:
        print("error: --runs must be at least 1", file=sys.stderr)
        return 2

    path = Path(args.queries)
    if not path.exists():
        print(f"error: queries file not found: {args.queries}", file=sys.stderr)
        return 2
    queries = json.loads(path.read_text(encoding="utf-8"))["queries"]
    if args.split != "all":
        queries = [q for q in queries if q.get("split") == args.split]
    if not queries:
        print("error: no queries selected", file=sys.stderr)
        return 2

    cmd = split_command(args.agent_cmd)
    if not cmd:
        print("error: --agent-cmd is empty", file=sys.stderr)
        return 2
    results, failures, skipped = [], 0, []
    for q in queries:
        triggers = 0
        completed = 0
        for _ in range(args.runs):
            try:
                proc = subprocess.run([*cmd, q["query"]], capture_output=True, text=True,
                                      encoding="utf-8", errors="replace", timeout=args.timeout)
            except subprocess.TimeoutExpired:
                skipped.append(f"q{q['id']}: no result after {args.timeout}s")
                continue
            except OSError as exc:
                print(f"error: cannot run {cmd[0]!r}: {exc}", file=sys.stderr)
                return 2
            if not proc.stdout.strip():
                detail = proc.stderr.strip()[:160] or "no stderr"
                skipped.append(f"q{q['id']}: empty transcript (agent exit {proc.returncode}, stderr: {detail})")
                continue
            completed += 1
            skill_read, final = parse_transcript(proc.stdout)
            if skill_read or API_MARKERS.search(final):
                triggers += 1
        rate = triggers / completed if completed else 0.0
        if completed:
            passed = rate >= args.threshold if q["should_trigger"] else rate < args.threshold
        else:
            passed = False   # nothing observed; never report an unrun query as a pass
        failures += 0 if passed else 1
        results.append({"id": q["id"], "split": q["split"], "should_trigger": q["should_trigger"],
                        "triggers": triggers, "runs": args.runs, "completed": completed,
                        "trigger_rate": rate, "passed": passed})
        if not args.json:
            print(f"q{q['id']:<3} {q['split']:<10} should_trigger={str(q['should_trigger']):<5} "
                  f"rate={rate:.2f} ({completed}/{args.runs} runs) {'PASS' if passed else 'FAIL'}")

    if args.json:
        print(json.dumps({"queries": results, "threshold": args.threshold, "failures": failures,
                          "skipped": skipped}, indent=2))
    else:
        for line in skipped:
            print(f"skipped {line}")
        print(f"failed {failures}/{len(results)} queries (threshold {args.threshold}, "
              f"{len(skipped)} run(s) skipped)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
