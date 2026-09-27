# Stage 5 — verdict

Run these from the project root, in this order:

```bash
python .agents/skills/crawl4ai/scripts/check_api.py   # names, parameters, result fields, documented defaults
python .style_check.py                                # pronouns, filler, emoji, repeated version target
python scripts/update_skill.py --check-only           # mirror baseline, coverage merge, gate roll-up
```

- Red gate → fix the cause the gate names. A name the new prose cites is merged into the generated
  regions by `update_skill.py`; a default that moved is corrected where the reference states it.
- Silence nothing: no checked name deleted, no expectation edited, no regex widened, unless the
  installed package is the thing that moved.
- The exit code of `update_skill.py --check-only` is the verdict: 0 means this pass left nothing
  behind, 1 means actions remain.

Finish the session with a short report:

1. files changed, one line each;
2. the three gate exit codes;
3. every action from `reports/skill-sync.md` still unresolved, with the reason it could not be closed
   in this pass.
