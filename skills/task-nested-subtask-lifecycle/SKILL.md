---
name: task-nested-subtask-lifecycle
description: "Use when a related TODO needs an independently managed child task."
version: 1.0.0
author: Hermes Agent
license: MIT
category: hermes
metadata:
  hermes:
    scenes: [hermes, common]
    tags: [task-framework, nested-task, subtask, lifecycle, containment]
---

# Nested Subtask Lifecycle

Use this optional skill when a TODO is strongly related to its parent but is
independently lifecycle-deliverable and does not fully overlap existing work.

## Create

Create a real, first-class child with the task-framework manager:

```bash
python3 skills/task-framework/scripts/manage_task.py create <name> \
  --parent <parent-hash-or-directory> --desc "Bounded child goal"
```

The child is created only under `<parent>/subtasks/` and receives its own
`TASK.md`, `MEMORY.md`, `CHANGELOG.md`, metadata, input, and output. Children
cannot create further children. Never hand-edit metadata or move child dirs.

## Route and verify

Record the child path or hash in the parent's TODO outcome and mark that TODO
`routed` with scope `nested`. The parent remains incomplete until its TODO is
routed and the child follows its own checklist lifecycle. `reindex` and the
stable task API expose parent/child relationships; root indexes list children
under their parent, not as independent root rows.

A child is valid only when its real path is contained by the exact parent's
`subtasks/` directory. Symlinks and paths outside that directory are rejected.
Reset clears only the selected child's generated output and preserves input.
