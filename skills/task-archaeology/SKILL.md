---
author: Hermes Agent
category: software-development
description: Reconstruct missing session context from canonical task artifacts and repository history.
license: MIT
metadata:
  hermes:
    scenes: [hermes, research]
    tags: [task-framework, archaeology, session-recovery, task-recovery, forensics]
    relations:
    - type: depends_on
      target: task-aware-project-work
      properties: {reason: canonical task context must be read in order, strength: strong}
    - type: complemented_by
      target: task-artifact-integrity
      properties: {reason: validates recovered artifact closure, strength: strong}
name: task-archaeology
platforms: [linux, macos]
version: 2.1.0
---

# Task Archaeology

Use when session history is missing or incomplete but the user provides a task name, hash, or directory.

## Recovery order

1. Resolve the task with `task_api.py describe <identifier>`; do not pass task directory names as session IDs.
2. If `runtime/` exists, read `runtime/INDEX.md` FIRST — it is the resumable execution snapshot after machine restart or context compression. Drill down from its rows into the item's `TODO.md` / `LOG.md` / `MEMORY.md` to locate unfinished (`todo`) or `blocked` work. Recovery relies on this on-disk state, never on chat history.
3. Read `TASK.md`, root `MEMORY.md`, and recent root `CHANGELOG.md`.
4. When hierarchical, read each relevant subsystem MEMORY and recent CHANGELOG.
5. Read `README.md` and `.hermes-task.json` for creation time, outputs, and relationships.
6. Resolve dependencies, related tasks, superseded tasks, and named outputs.
7. Inventory `input/`, `output/docs/`, `output/logs/`, and scripts.
8. Cross-reference repository branches and commits by timestamps and artifact paths.
9. State what is directly evidenced, inferred, missing, and still blocked.

Task artifacts are evidence of task state, not a verbatim transcript. Never invent user statements from file outcomes.

## Result

Return the reconstructed goal, decisions, produced artifacts, verification, unresolved issues, and exact continuation point, with file paths for every claim.
