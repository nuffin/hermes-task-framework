---
name: task-lifecycle-portability
description: Task migration, export/import, and symlink-protection model. Covers tar.gz
  snapshots, double-git repos for metadata + execution history, and manage.py lifecycle
  commands (export/import/rebuild/relink).
version: 1.0.0
category: software-development
platforms:
- linux
- macos
author: Hauzer S. Lee
license: MIT
metadata:
  hermes:
    tags:
    - migration
    - software-development
---


# Task Lifecycle & Portability

Manages task portability between machines and protects task metadata from destructive cleanup.

## Symlink Protection Model

Three core files in each task directory are symlinks to `~/.hermes/personal/tasks/<hash>/`:

| Symlink (in task dir) | Target | Content |
|----------------------|--------|---------|
| `TASK.md` | `task.md` | Checklist, status, goal |
| `TASK_MEMORY.md` | `memory.md` | Decision log, per-session notes |
| `.hermes-task.json` | `meta.json` | Hash, outputs, dependencies |

Personal storage layout:

```
~/.hermes/personal/tasks/<hash>/
├── .git/                    ← tracks task.md, memory.md, meta.json history
├── task.md                  ← TASK.md actual content
├── memory.md                ← TASK_MEMORY.md actual content
└── meta.json                ← .hermes-task.json actual content
```

**Protection guarantees:**
- `rm -rf` entire task dir → symlinks break, actual data in `~/.hermes/personal/tasks/<hash>/` remains
- Pipeline exclusion-based cleanup can't reach symlinked files
- `manage.py relink <hash>` restores broken symlinks in seconds
- Each `<hash>/` has independent git repo for metadata change history

## Cleanup Discipline

**Only `output/` is safe to delete:**
- `task_reset --hard` = `rm -rf output/` + reset checkbox
- Never use exclusion-based deletion (`find . -not -name 'X' -delete` or positive-listing `rm -rf tts-*/ RECORDING.md ...`) — these always miss something or catch too much
- All generated files (RECORDING.md, COMPOSITING.md, IMAGE_SLIDESHOW.md, SUBTITLE_SPEC.md, phase directories, logs) live in `output/`

## Directory Boundary

```
tasks/<ts>.<name>-<hash6>/
├── TASK.md              (symlink)
├── TASK_MEMORY.md       (symlink)
├── .hermes-task.json    (symlink)
├── input/               ← SOURCE: user-provided, NEVER delete
└── output/              ← GENERATED: pipeline owns this, safe to rm -rf
```

## Export / Import / Rebuild

`manage.py <hash>` commands:

| Command | What it does |
|---------|-------------|
| `export <hash>` | Follow symlinks, resolve to real content, produce `tasks/<ts>.<name>-<hash>.tar.gz` (excludes `output/`, includes `input/` + symlink targets + both `.git/` dirs) |
| `import <tar.gz>` | Extract to `tasks/` directory, create `~/.hermes/personal/tasks/<hash>/` if needed, restore all symlinks |
| `rebuild <hash>` | Find latest `<hash>.tar.gz` in `tasks/`, extract, restore symlinks. Generates semantic directory name from TASK.md title |
| `relink <hash>` | Recreate broken symlinks for an existing task directory (no tarball needed) |

**Actual script path:**
`~/.hermes/skills/software-development/task-framework/scripts/manage_task.py`

Usage: `python3 <path> <command> <arg>`

**Export behavior:**
- `tar --dereference` — follows symlinks, archive contains actual content, not symlink paths
- Output dir is excluded (it's regenerable via pipeline)
- Both git repos (`tasks/<dir>/.git/` and `~/.hermes/personal/tasks/<hash>/.git/`) are preserved in the tarball
- Import restores both git histories independently

**Cross-machine strategy:**
- No automatic merge — each machine's copy is an independent task
- To combine work from two machines: create a new task referencing both via `ref:<hash>/...`
- `tar.gz` in git repo acts as backup even if personal `~/.hermes/personal/tasks/` is not pushed

## Old Tasks (Migration)

- Tasks already in `input/` + `output/` model: add symlinks via `manage.py init`
- Legacy flat tasks (REQUIREMENTS.md + images/ at root, no input/output): migrate if feasible; abandon if too old
- When you discover TASK.md is missing: **regenerate immediately from TASK_MEMORY.md + directory artifacts**, do not skip or defer

## TASK.md Recovery (Edge Cases)

See `references/task-recovery-procedure.md` for the full step-by-step TASK.md recovery process when the file is missing or corrupted. Key principles:

1. **Check the symlink target first** — if the hash-based personal backup exists, recovery is instant via `manage_task.py relink <hash>`
2. **Identify task type** — scan for signature files (REQUIREMENTS.md + RECORDING.md etc.) and load the task-type's governing skill for its defined phase structure
3. **Map evidence to phases** — cross-reference output directories, `.hermes-task.json` outputs, and TASK_MEMORY.md against the skill's phase templates
4. **Write TASK.md** following the skill's template — don't invent phases, don't reorder

🔴 Critical: Do NOT guess phase structure from memory. Load the domain skill that governs this task type and use its defined phases. Verify each phase's output file exists before marking complete.

**Real-world example:** `references/task-recovery-5d5a1a-example.md` — step-by-step walkthrough of recovering 5d5a1a's TASK.md after it was lost to exclusion-based cleanup.

## Pipeline Output Model (Design)

See `references/output-model-design.md` for the full 2026-06-11 design rationale. The core decisions:

- **Output isolation**: All generated artifacts in `output/`, user materials in `input/`
- **Cleanup strategy**: `rm -rf output/` — never exclusion-based deletion
- **Symlink protection**: Three metadata files symlinked to personal storage `~/.hermes/personal/tasks/<hash>/`
- **Manage tool**: `manage_task.py` with `init/export/import/rebuild/relink/reindex` commands

**Implementation:** `references/pipeline-output-transition.md` — detailed diff of what changed in pipeline.py to adopt the output/ model.

## Pitfalls
| `ref:` resolution breaks when hash-only (no directory match) | `.hermes-task.json` outputs should use `ref:hash/output_name` format. Directory must contain the hash in its name for `ref:` glob resolution. |
| Pipeline writes spec files to task root instead of output/ | All generated specs (RECORDING.md, COMPOSITING.md, IMAGE_SLIDESHOW.md, SUBTITLE_SPEC.md) belong in `output/`. Update pipeline scripts if they write to root. |
