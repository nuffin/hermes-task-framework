---
author: Hauzer S. Lee
category: software-development
description: Task migration, export/import, and file-protection model. Covers tar.gz
  snapshots and manage.py lifecycle commands (export/import/rebuild).
license: MIT
metadata:
  hermes:
    scenes:
    - hermes
    - devops
    tags:
    - software-development
    - task-migration
    - export-import
    - file-protection
    - python
    - hermes
name: task-lifecycle-portability
platforms:
- linux
- macos
version: 1.0.0
---


# Task Lifecycle & Portability

Manages task portability between machines and protects task metadata from destructive cleanup.

## File Protection Model

All task files live directly in the task directory — no mirror directories, no symlinks. The task directory is the single source of truth.

**Protection guarantees:**
- `rm -rf output/` only touches generated files; metadata files (TASK.md, CHANGELOG.md, .hermes-task.json) in the task root and user files in `input/` are safe
- Pipeline exclusion-based cleanup can't reach task metadata
- All task files are in one place, making export/import straightforward

## Cleanup Discipline

**Only `output/` is safe to delete:**
- `task_reset --hard` = `rm -rf output/` + reset checkbox
- Never use exclusion-based deletion (`find . -not -name 'X' -delete` or positive-listing `rm -rf tts-*/ RECORDING.md ...`) — these always miss something or catch too much
- All generated files (RECORDING.md, COMPOSITING.md, IMAGE_SLIDESHOW.md, SUBTITLE_SPEC.md, phase directories, logs) live in `output/`

## Directory Boundary

```
tasks/<ts>.<name>-<hash6>/
├── TASK.md
├── CHANGELOG.md
├── .hermes-task.json
├── input/               ← SOURCE: user-provided, NEVER delete
└── output/              ← GENERATED: pipeline owns this, safe to rm -rf
```

## Export / Import / Rebuild

`manage.py <hash>` commands:

| Command | What it does |
|---------|-------------|
| `export <hash>` | Package task directory as `tasks/<ts>.<name>-<hash>.tar.gz` (excludes `output/`, includes `input/` + metadata files) |
| `import <tar.gz>` | Extract to `tasks/` directory, restore all files |
| `rebuild <hash>` | Find latest `<hash>.tar.gz` in `tasks/`, extract. Generates semantic directory name from TASK.md title |

**Actual script path:**
`~/.hermes/skills/software-development/task-framework/scripts/manage_task.py`

Usage: `python3 <path> <command> <arg>`

**Export behavior:**
- Archive contains actual file content (no symlinks involved)
- Output dir is excluded (it's regenerable via pipeline)
- `tar.gz` acts as a portable backup that can be committed to git

**Cross-machine strategy:**
- No automatic merge — each machine's copy is an independent task
- To combine work from two machines: create a new task referencing both via `ref:<hash>/...`
- `tar.gz` in git repo acts as backup

## Old Tasks (Migration)

- Tasks already in `input/` + `output/` model: use `manage_task.py init` for initial setup
- Legacy flat tasks (REQUIREMENTS.md + images/ at root, no input/output): migrate if feasible; abandon if too old
- When you discover TASK.md is missing: **regenerate immediately from CHANGELOG.md + directory artifacts**, do not skip or defer

## TASK.md Recovery (Edge Cases)

See `references/task-recovery-procedure.md` for the full step-by-step TASK.md recovery process when the file is missing or corrupted. Key principles:

1. **Check the task directory** — verify if TASK.md exists in the task directory; if corrupted, reconstruct from CHANGELOG.md + artifacts
2. **Identify task type** — scan for signature files (REQUIREMENTS.md + RECORDING.md etc.) and load the task-type's governing skill for its defined phase structure
3. **Map evidence to phases** — cross-reference output directories, `.hermes-task.json` outputs, and CHANGELOG.md against the skill's phase templates
4. **Write TASK.md** following the skill's template — don't invent phases, don't reorder

🔴 Critical: Do NOT guess phase structure from memory. Load the domain skill that governs this task type and use its defined phases. Verify each phase's output file exists before marking complete.

**Real-world example:** `references/task-recovery-5d5a1a-example.md` — step-by-step walkthrough of recovering 5d5a1a's TASK.md after it was lost to exclusion-based cleanup.

## Pipeline Output Model (Design)

See `references/output-model-design.md` for the full 2026-06-11 design rationale. The core decisions:

- **Output isolation**: All generated artifacts in `output/`, user materials in `input/`
- **Cleanup strategy**: `rm -rf output/` — never exclusion-based deletion
- **File protection**: Metadata files (TASK.md, CHANGELOG.md, .hermes-task.json) live directly in task directory — single source of truth
- **Manage tool**: `manage_task.py` with `init/export/import/rebuild/relink/reindex` commands

**Implementation:** `references/pipeline-output-transition.md` — detailed diff of what changed in pipeline.py to adopt the output/ model.

## Pitfalls
| `ref:` resolution breaks when hash-only (no directory match) | `.hermes-task.json` outputs should use `ref:hash/output_name` format. Directory must contain the hash in its name for `ref:` glob resolution. |
| Pipeline writes spec files to task root instead of output/ | All generated specs (RECORDING.md, COMPOSITING.md, IMAGE_SLIDESHOW.md, SUBTITLE_SPEC.md) belong in `output/`. Update pipeline scripts if they write to root. |
