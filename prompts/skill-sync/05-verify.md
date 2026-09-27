# Stage 5 — verdict

Run these from the project root, in this order:

```bash
python .agents/skills/crawl4ai/scripts/check_api.py       # names, parameters, result fields, documented defaults
python .style_check.py .agents/skills/crawl4ai            # pronouns, filler, emoji, repeated version target
python scripts/update_skill.py --check-only --json        # mirror baseline, coverage merge, gate roll-up
```

- Red gate → fix the cause the gate names. A name the new prose cites is merged into the generated
  regions by `update_skill.py`; a default that moved is corrected where the reference states it.
- Silence nothing: no checked name deleted, no expectation edited, no regex widened, unless the
  installed package is the thing that moved.
- `--check-only` diffs the mirror against the *committed* one, and this pass runs before that commit:
  its exit code stays 1 for the pages the sync just brought in, even after they are handled. Read the
  `actions` list it prints, not the exit code — the orchestrator re-derives the verdict from the tree
  this session leaves behind, and that is what the run is judged on.
- The `probes` block is the same rule: a value that moved is re-observed here, and an unavailable probe
  is reported, never assumed.

Finish the session with a short report:

1. files changed, one line each;
2. the gate exit codes;
3. every action from `reports/skill-sync.md` still unresolved, with the reason it could not be closed
   in this pass.
