---
author: Hermes Agent
category: software-development
description: Load canonical root and subsystem task context before continuing project work.
license: MIT
metadata:
  hermes:
    scenes: [hermes, coding]
    tags: [task-framework, task-context, discovery, continuation, project-management]
    relations:
    - type: depends_on
      target: task-context-storage
      properties: {reason: defines context ownership, strength: strong}
    - type: depends_on
      target: compact-directory-memory
      properties: {reason: defines hierarchical read protocol, strength: strong}
name: task-aware-project-work
platforms: [linux, macos]
version: 2.0.0
---

# Task-Aware Project Work

Use when continuing a task by name/hash, returning to project work tied to a task, or before creating project artifacts that may already exist.

## Protocol

1. Resolve the task with `task_api.py describe <identifier>`.
2. Read `TASK.md`, root `MEMORY.md`, and recent root `CHANGELOG.md`.
3. Detect `.hermes-task.json.memory_layout` or `memories/`.
4. Identify the target subsystem and read its full MEMORY plus recent CHANGELOG.
5. Resolve project/repository paths from task context and verify existing artifacts before creating anything.
6. If a hierarchical subsystem is missing, load `compact-directory-memory` and create the complete pair before source changes.

Legacy `TASK_MEMORY.md` is not canonical. Use it only as archaeological evidence when canonical files are absent.

## Pitfalls

- A ticket is not a task-framework task.
- Never start implementation before loading task context.
- Search actual repositories before concluding an artifact was deleted.
- Do not duplicate a project or subsystem because another session used a different path.
