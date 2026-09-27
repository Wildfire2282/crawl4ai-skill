"""Style gate for the skill's prose: no pronouns, contractions, filler or emoji.

The skill is read by an agent, so its prose is written in the register of a reference: no second
person, no marketing filler, and the version target stated once. This gate is a real check — it exits
non-zero when it finds an issue, because an unattended run has to stop on a red gate rather than
commit prose that breaks the register.

Usage: python .style_check.py [skill-directory]   # default: .agents/skills/crawl4ai
Exit codes: 0 clean, 1 one or more issues (printed with file and line).
"""

import re
import sys
from pathlib import Path

skill = Path(sys.argv[1] if len(sys.argv) > 1 else ".agents/skills/crawl4ai")
files = sorted([skill / "SKILL.md",
                *sorted((skill / "references").glob("*.md")),
                skill / "scripts/check_api.py",
                skill / "evals/README.md",
                skill / "evals/run_trigger.py"])
PRONOUNS = re.compile(r"\b(you|your|yours|yourself|we|us|our|ours)\b", re.IGNORECASE)
CONTRACTIONS = re.compile(r"\b\w+n't\b|\b(it|that|there|what|let|here|who|this|they)'s\b", re.IGNORECASE)
COLLOQUIAL = re.compile(r"\b(simply|easily|basically|really|very|pretty|a lot|lots of|obviously|of course|"
                        r"bites?|cheap|grab|stuff|nice|good idea|in order to|it is worth|remember that|"
                        r"note that|keep in mind|aim for|try to|make sure)\b", re.IGNORECASE)
EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF]")
issues = 0


def prose(t: str) -> str:
    t = re.sub(r"```.*?```", "", t, flags=re.DOTALL)
    return re.sub(r"`[^`]*`", "", t)


for f in files:
    text = f.read_text(encoding="utf-8")
    body = prose(text)
    found = []
    for label, pat in (("pronoun", PRONOUNS), ("contraction", CONTRACTIONS), ("colloquial", COLLOQUIAL), ("emoji", EMOJI)):
        for m in pat.finditer(body):
            found.append(f"{label}: L{body[:m.start()].count(chr(10))+1}: {m.group(0)!r}")
    if f.suffix == ".md" and len(re.findall(r"0\.9\.x", body)) > 1:
        found.append("target-version repeated")
    print(f"{f.relative_to(skill).as_posix():<28} lines={len(text.splitlines()):>4}")
    for i in found:
        print("   ", i)
        issues += 1
print("issue count:", issues)
raise SystemExit(1 if issues else 0)
