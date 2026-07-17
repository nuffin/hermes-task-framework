# Auto-Runner (run.py) Pattern

## When to Use

Multi-phase tasks with a checklist in TASK.md. Create a single `run.py` at the task root that dispatches to individual phase scripts.

## Structure

```python
./run.py                    — auto: find first unchecked item & execute
./run.py phase<N>           — run specific phase
./run.py list               — show checklist status
```

## Auto Mode Logic

1. Read TASK.md checklist, find first `[ ]` item
2. If it's a **BREAK**, mark it `[x]` and continue to next item
3. Execute phases until next `[ ] BREAK` or end of list
4. Mark each completed phase as `[x]`

## Phase Runners

Each phase runner calls an individual script (e.g. `scripts/gen_tts.py`, `scripts/record_timeline.py`, `scripts/composite.py`).

## Unimplemented Phases

Phases without an implementation should return `True` (skip, don't fail) so the auto-runner can progress past them to the next BREAK.

## Venv

Use `~/.venvs/playwright/bin/python` if available (has playwright, edge-tts, matplotlib, Pillow).
