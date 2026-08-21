---
author: Hermes Agent
category: software-development
description: "Manage task lifecycle safely: find-before-create, rename/delete cascades, and index consistency."
license: MIT
metadata:
  hermes:
    scenes: [hermes, coding]
    tags: [task-framework, lifecycle, task-management, preflight, rename, deletion]
    relations:
    - type: depends_on
      target: task-framework
      properties: {reason: task-framework owns lifecycle commands and storage, strength: strong}
    - type: complemented_by
      target: task-timestamp-convention
      properties: {reason: naming policy is maintained separately, strength: strong}
name: task-lifecycle-discipline
platforms: [linux, macos]
version: 2.0.0
---

# Task Lifecycle Discipline

Owns lifecycle policy around task-framework commands. Agents do not create, rename, or delete task directories with raw filesystem commands.

## Find before create

Before creating a task:

1. Use `task_api.py search <terms>` against the configured task root.
2. Reuse a matching active task when its scope already covers the request.
3. Create only when no existing task matches.
4. Use a specific kebab-case name that includes the system/domain and deliverable.

Generic file-writing does not automatically require a task. Create one for durable multi-step work, explicit task requests, cross-session coordination, or task-framework pipelines.

## Creation

Use only:

```bash
python3 <task-framework>/scripts/manage_task.py create <name> --desc "<goal>"
```

Creation must produce `TASK.md`, `README.md`, `MEMORY.md`, `CHANGELOG.md`, `.hermes-task.json`, `input/`, `output/docs/`, `output/logs/`, and `scripts/`, then regenerate root indexes.

Never hand-generate hashes or metadata. `HERMES_TASKS_ROOT` is canonical; `HERMES_TASKS_DIR` is compatibility-only.

## Status and reset

Use `manage_task.py status` and `manage_task.py reset`. Hard reset clears only `output/`, resets non-DONE checkboxes, preserves `input/`, root context files, `memories/`, and metadata, then reindexes.

## Rename

Task rename is a lifecycle operation, not raw `mv`:

1. Resolve the task through `task_api.py describe`.
2. Validate the new lowercase kebab-case name and preserve the hash suffix.
3. Copy to the new directory, verify a relative-path/type/size/SHA-256 manifest, then remove the old directory.
4. Update `# Task:`, `.hermes-task.json.name`, absolute references, named outputs, and related-task links.
5. Append CHANGELOG entries and regenerate indexes.

A future `manage_task.py rename` command should automate this procedure; until then, use `task-artifact-integrity` and a permanent migration script.

## Delete

Deletion requires an exact resolved task path and explicit user authorization. Before deletion:

1. Read task context and related-task closure.
2. Confirm no required input/output or downstream reference would be lost.
3. Archive only when requested or needed for rollback.
4. Delete the exact task directory and regenerate indexes.

Never delete by glob, topic fragment, process output, or inferred path.

## Adapter boundary

External systems use `task_api.py` for resolution, search, metadata, and extension fields. They do not parse directory names, edit `.hermes-task.json` directly, or hardcode `update-index.py` paths.
