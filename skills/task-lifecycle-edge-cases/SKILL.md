---
name: task-lifecycle-edge-cases
description: "Edge-case operations for task lifecycle — TASK.md recovery after loss, task resurrection from artifacts, conflict resolution when phase directories diverge from checklist."
version: 1.0.0
author: Hauzer S. Lee
license: MIT
category: software-development
platforms: [linux, macos]
metadata:
  hermes:
    tags: ['task', 'lifecycle', 'recovery', 'edge-case']
    related_skills: ['task-framework', 'browser-screen-record-task']
---

# Task Lifecycle Edge Cases

Recurring edge cases in task lifecycle management that the standard `task-framework` workflow doesn't explicitly cover.

## TASK.md Recovery

When a task directory exists but `TASK.md` is missing (deleted, never created, or corrupted), reconstruct it from surrounding artifacts.

### Step 1: Gather evidence

| Source | What it tells you |
|--------|------------------|
| `.hermes-task.json` | hash, name, outputs, dependencies |
| `TASK_MEMORY.md` | last session's state, what was done, what broke, what's next |
| `input/REQUIREMENTS.md` | original task spec |
| `output/` | all generated files |
| `.hermes-task.json` → `outputs` | what was produced and where |
| Root index (`tasks/index.md`) | aggregated status from last index run |

### Step 2: Identify task type and load its governing skill

**Critical step.** Do NOT guess phase structure from memory or from other similar tasks.

1. Scan directory for type-signature files — `REQUIREMENTS.md` + `RECORDING.md` + `COMPOSITING.md` → video-production task
2. Load the relevant skill that defines this task type:
   - Video production → `browser-screen-record-task`
   - Document analysis → `task-framework`'s `references/task-types/`
   - Other → the skill used to create the task (check `.hermes-task.json` or TASK_MEMORY.md)
3. Read the skill's phase/流程/Checklist structure carefully before writing

### Step 3: Map evidence to skill's phase structure

Cross-reference:
- Phase directories in `output/` → confirm each matches a skill-defined phase
- Outputs in `.hermes-task.json` → map each to the right phase's product (note: paths may be `output/...` prefixed for post-migration tasks)
- TASK_MEMORY.md execution notes → confirm sequence matches skill's defined order
- Parallel deps → check `和 X 同步进行` annotations match skill's flow table

### Step 4: Write TASK.md

Follow the skill's template for:
- `## Skills` — list all skills the task type requires
- `## Data Flow` — map skill's phase table to actual directory hashes
- `## Checklist` — use skill's standard phase names and dependency annotations
- Mark all verified-completed items `[x]`
- Add `## Notes` for task-specific context

Key formatting:
- Phase dirs use `<short-name>-<hash6>/` (from actual dirs or .hermes-task.json)
- Checklist `()` uses descriptive phase names only, no hashes
- `和 Phase X 同步进行` for parallel phases
- `等待 Phase X 完成` for dependency phases

### Step 5: Verify before marking done

Only mark phases `[x]` if the output artifact exists and can be verified (stat the file). If a phase was in-progress but incomplete, mark `[ ]` and note in `## Notes`.

### Step 6: Update indexes

```bash
python3 ~/.hermes/skills/software-development/task-framework/scripts/update-index.py
```

## Pitfalls

- 🔴 **Do NOT infer phase structure from prior conversation** — load the domain skill that governs this task type and use its defined phases
- 🔴 **Do NOT invent phases that don't match the skill's template** — subtitle-compositing and timeline-chart-preview are NOT separate phases in the standard video-production skill; they are subsumed by composite
- 🔴 **Do NOT reorder phases from the skill's defined sequence** — the skill encodes the correct dependency graph (e.g., timeline-composer must run after TTS to know audio durations, but before recording)
- 🔴 **Always verify material existence** — directory existing ≠ phase completed; check for the actual output file
- 🔴 **BREAK placement** — keep BREAKs exactly where the skill template places them, not where you guess they should be
