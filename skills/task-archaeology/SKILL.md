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
version: 2.0.0
---

# Task Archaeology

Use when session history is missing or incomplete but the user provides a task name, hash, or directory.

## Recovery order

1. Resolve the task with `task_api.py describe <identifier>`; do not pass task directory names as session IDs.
2. Read `TASK.md`, root `MEMORY.md`, and recent root `CHANGELOG.md`.
3. When hierarchical, read each relevant subsystem MEMORY and recent CHANGELOG.
4. Read `README.md` and `.hermes-task.json` for creation time, outputs, and relationships.
5. Resolve dependencies, related tasks, superseded tasks, and named outputs.
6. Inventory `input/`, `output/docs/`, `output/logs/`, and scripts.
7. Cross-reference repository branches and commits by timestamps and artifact paths.
8. State what is directly evidenced, inferred, missing, and still blocked.

Task artifacts are evidence of task state, not a verbatim transcript. Never invent user statements from file outcomes.

## Result

Return the reconstructed goal, decisions, produced artifacts, verification, unresolved issues, and exact continuation point, with file paths for every claim.
