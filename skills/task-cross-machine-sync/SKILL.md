---
author: Hermes Agent
category: software-development
description: Synchronize a configured task root across machines with Git while preserving task indexes and context integrity.
license: MIT
metadata:
  hermes:
    scenes: [hermes, coding, devops]
    tags: [task-framework, git, cross-machine, synchronization, portability]
    relations:
    - type: depends_on
      target: task-lifecycle-portability
      properties: {reason: export/import remains the one-task fallback, strength: strong}
    - type: complemented_by
      target: task-artifact-integrity
      properties: {reason: validates context after transport, strength: strong}
name: task-cross-machine-sync
platforms: [linux, macos]
version: 2.0.0
---

# Task Cross-Machine Sync

Synchronizes the configured `$HERMES_TASKS_ROOT` as a Git repository. It contains no private repository name, fixed machine role, credentials, or mandatory remote.

## Configuration inputs

- task root from task-framework resolution;
- Git remote and branch supplied by the environment/user;
- optional machine role and conflict policy supplied outside this skill;
- optional Git LFS policy for large artifacts.

## Preconditions

1. Confirm the exact task root and Git repository status.
2. Ensure the remote/branch were explicitly configured.
3. Regenerate `README.md` and `TASKS.md` before commit.
4. Check for nested repositories and machine-specific artifacts.
5. Never push unless the user explicitly requests it.

## Track/ignore policy

Track task metadata, context, inputs, outputs, and verification artifacts unless the task repository policy says otherwise. Ignore environment rebuild products such as `.venv/`, `node_modules/`, caches, editor files, and sync-conflict metadata. Nested external repositories require an explicit policy; do not accidentally stage their object databases.

## Sync sequence

1. Fetch and inspect divergence.
2. Default to fast-forward only; stop on divergence for explicit reconciliation.
3. Resolve append-only CHANGELOG conflicts by preserving both chronological entries.
4. Resolve MEMORY conflicts semantically: retain current stable facts, remove stale duplicates.
5. Run task index regeneration and directory-context verification.
6. Commit task changes with task hash/name in the message.
7. Push only after explicit authorization.

## Fallbacks

Use `task-lifecycle-portability` export/import for one-task transfer, offline movement, or when the task root is not a shared Git repository.

## Permanent tooling

```bash
python3 scripts/task_git_sync.py status [--tasks-root <path>]
python3 scripts/task_git_sync.py pull --tasks-root <path> --remote <remote> --branch <branch> --execute
python3 scripts/task_git_sync.py push --tasks-root <path> --remote <remote> --branch <branch> --execute
```

Mutation commands refuse dirty worktrees, missing remotes/branches, absent `--execute`, non-fast-forward pulls, and pushes when the remote is ahead. The script never creates commits or repositories.
