# TASK.md Recovery Procedure

When a task directory exists but `TASK.md` is missing (deleted, never created, or corrupted), reconstruct it from surrounding artifacts.

## Step 0: Check symlink target first

If the task has hash-based naming (rightmost 6 chars = `<hash6>`), check `~/.hermes/personal/tasks/<hash>/task.md`:

```bash
ls -la ~/.hermes/personal/tasks/<hash>/task.md
# If exists → restore with:
python3 ~/.hermes/skills/software-development/task-framework/scripts/manage_task.py relink <hash>
```

If the personal backup exists, symlink recovery is instant.

## Step 1: Gather evidence

| Source | What it tells you |
|--------|------------------|
| `~/.hermes/personal/tasks/<hash>/task.md` | content backup — instant recovery via relink |
| `~/.hermes/personal/tasks/<hash>/memory.md` | TASK_MEMORY.md content backup |
| `.hermes-task.json` | hash, name, outputs, dependencies |
| `TASK_MEMORY.md` | last session's state, what was done, what broke |
| `input/REQUIREMENTS.md` | original task spec |
| `output/` | all generated files |
| Root index (`tasks/TASKS.md`) | aggregated status from last index run |

## Step 2: Identify task type and load its governing skill

Scan directory for type-signature files — `REQUIREMENTS.md` + `RECORDING.md` + `COMPOSITING.md` → video-production task. Load the relevant skill that defines this task type's phases.

> 🔴 Do NOT guess phase structure from memory or from other similar tasks. Load the domain skill and use its defined phases.

## Step 3: Map evidence to skill's phase structure

Cross-reference:
- Phase directories in `output/` → confirm each matches a skill-defined phase
- Outputs in `.hermes-task.json` → map each to the right phase's product
- TASK_MEMORY.md execution notes → confirm sequence matches skill's defined order
- Parallel deps → check annotations match skill's flow table

## Step 4: Write TASK.md

Follow the skill's template for format. Use the skill's standard phase names and dependency annotations. Mark all verified-completed items `[x]`.

## Step 5: Verify before marking done

Only mark phases `[x]` if the output artifact exists and can be verified. If a phase was in-progress but incomplete, mark `[ ]` and note in `## Notes`.

## Step 6: Update indexes

```bash
python3 ~/.hermes/skills/software-development/task-framework/scripts/update-index.py
```

## Pitfalls

- 🔴 **Do NOT infer phase structure from prior conversation** — load the domain skill
- 🔴 **Do NOT invent phases that don't match the skill's template**
- 🔴 **Do NOT reorder phases from the skill's defined sequence**
- 🔴 **Always verify material existence** — directory existing ≠ phase completed
- 🔴 **BREAK placement** — keep exactly where the skill template places them
