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

Mutation commands `pull` and `push` refuse dirty worktrees, missing remotes/branches, absent `--execute`, non-fast-forward pulls, and pushes when the remote is ahead. These strict commands still never create commits or repositories.

## Opt-in unattended checkpoint sync (Linux)

The separate `sync` command is for a tasks-only Git root whose owner has authorized
automatic commits and normal pushes. It never creates a repository, rewrites remote
history, changes signing policy, starts an LLM, claims task completion, or installs a
scheduler. Run it from outside the task root using an external hourly scheduler
(for example a systemd user timer, independent of the Hermes gateway).

```bash
python3 scripts/task_git_sync.py sync --config /absolute/path/task-sync.json --execute
```

The JSON config has these exact fields (unknown fields are rejected):

```json
{
  "tasks_root": "/absolute/path/to/tasks",
  "remote": "origin",
  "remote_url": "ssh://git@example.invalid/owner/tasks.git",
  "branch": "main",
  "node_id": "node-one",
  "auto_push": true,
  "cooperative_writers": true,
  "max_blob_bytes": 10485760,
  "command_timeout_seconds": 30,
  "network_retries": 2
}
```

All fields except the last three are required. `tasks_root` must resolve to the exact
repository top-level and the current branch must be `main`. Both fetch and push URL
lists must contain exactly the literal `remote_url`; SCP-style spellings are not
normalized or repaired. `auto_push` and `cooperative_writers` must be JSON `true`.
The latter is the owner's declaration that uncoordinated writers are excluded; it
is **not evidence** that arbitrary applications have acquired a lock. No config
or real tasks root is modified by installation of this implementation.

### On-demand interactive task windows

When an explicitly named task needs human GPG/MFA/login interaction on an executor,
follow `references/on-demand-interactive-task-windows.md`. It defines the optional
`hermes-runtime:task-<hash6>` convention. Ordinary checkpoint runs remain noninteractive
and do not create a tmux window.

### Transaction and history

1. Acquire the nonblocking shared root writer lease; refuse known live Python/Hermes
   processes whose `/proc/<pid>/cwd` is inside the task root, including idle sessions.
   Shell CWD alone is not considered evidence of a writer. The process is never killed.
2. Refuse interrupted merge/rebase/cherry-pick/revert and busy index operations.
3. Snapshot the original index and then all working changes with a private index.
   Git ignores are respected; tracked deletions are checkpointed. In an isolated
   worktree, commit staged state first and remaining changes second. Normal `git commit`
   honors hooks and configured signing; failure blocks sync, **never** falls back
   unsigned. Checkpoint tree changes made by hooks also require review.
4. Keep local `refs/task-sync/<node>-<transaction>/{before,staged,working,integrated}`.
   Rebase actual checkpoint/user commits, not a squashed synthetic replacement.
   Only conflicting root `README.md`/`TASKS.md` are mechanically discarded in favor
   of the integrated version. Any task-content conflict stops for human recovery in
   the isolated worktree; main is not put into rebase conflict.
5. Reject absolute, missing, task-escaping, canonical-metadata, and root-index symlinks before generation; permit only an existing relative target whose resolved path stays within the same task root. Write root indexes by atomic regular-file replacement rather than opening existing targets for writing. Regenerate the root indexes **after** integration and commit only a changed tree. Each completed sync records a task-scope symlink post-flight in its transaction journal.
   Repeated idle runs after first normalization do not create commits.
6. Push without force. A rejected push retries bounded fetch/rebase from the original
   checkpoint. Verify the exact remote head after push. Before promotion compare
   the local content/index/HEAD snapshot again, check incoming ignored/untracked
   obstructions, and use checked index/worktree transitions, never `reset --hard` or
   `clean`. New edits cause a refusal; an already successful push may still remain
   published when a later local promotion is refused.

New/modified candidate blobs are size-limited; unchanged historical large blobs are
not rejected. New/changed credential filenames, numbered `.git.N` backup content and
nested gitlinks are refused. This filename denylist is **not a secret scanner**.
Unchanged historical backups/gitlinks and ignored historical content are not scanned
recursively. Snapshots hash tracked/eligible untracked regular files in chunks, with
a deadline, rather than traversing ignored build trees or nested repository contents.

### Writer coordination and limits

`task-framework/scripts/task_write_lock.py` supplies `task_writer_lock(root)` and
`child_lease(root)` for cooperating tools. The canonical `manage_task.cmd_*` commands,
JSON API `command_*` functions, and direct index-generator CLI participate. The index
subprocess receives a verified inherited lease descriptor to avoid self-deadlock.
Imported low-level file-writing helpers, standalone todo-lifecycle operations,
third-party plugins, editors, shell writes, and older deployed framework copies are
**not universally covered**. They must be quiesced or explicitly wrapped in the same
lease. An idle live Hermes task session can therefore block every hourly run until
its owner moves/exits it; the scheduler must report that as skipped/blocked, not
success. There is no bypass flag for the live-process guard.

Git/filesystem promotion is not an atomic operation against arbitrary writers.
Fingerprints reduce the race window but cannot eliminate edits between checking and
writing. Do not enable automatic promotion where the cooperative-writer assumption
cannot be enforced. Mount failures, special files, malicious hooks, or processes that
escape their process group are outside the safe operating contract.

Each Git command/network operation is bounded (default 30 seconds, maximum 60),
with at most `network_retries + 1` push attempts (maximum 6) and an approximately
180-second transaction budget. Timed-out Git commands kill only their owned process
group, including ordinary SSH/GPG/hook descendants. An external systemd service
should additionally use `TimeoutStartSec=180` and `KillMode=control-group` as the
whole-process-tree backstop. No global process kill is used.

### Recovery and deployment

The shared Git common directory holds untracked `task-sync/` state: `writer.lock`,
`journal.json` (latest state), append-only per-transaction event JSON, original index
backup during promotion, and retained isolated recovery worktrees. Conflict,
interrupted promotion, or dirty recovery worktree phases block later automatic runs.
Do not delete recovery data to make a timer green. Inspect the recorded refs/index,
resolve in the isolated worktree, and verify local and remote contents before an
operator archives the latest journal to acknowledge recovery. Immutable event
records and backup refs should remain available; there is no automatic retention
pruning. Clean failed-push worktrees are removed and the next run may retry while
checkpoint refs and event records remain.

Deploy a versioned full release snapshot without overwriting existing checkout or
remote repositories. All writers requiring coordination need the corresponding new
writer implementation; a standalone scheduler-only update is not full coordination.
Unattended GPG/pinentry or authentication failure is a **blocked signing/authentication
result**, not a reason to disable signing or alter remote URLs. Report scheduler
installation, fixture tests, real-node signing, and real-node synchronization as
separate evidence; none implies the others.

For older deployed framework revisions, a minimal adoption backport is the new
`task_write_lock.py`, the `manage_task.py` command wrappers plus inherited-lease
subprocess change, equivalent `task_api.py` wrappers **only where that file already
exists**, and the index-generator lease/atomic-write safety changes. Apply that diff
against the exact preserved deployed revision after a clean applicability check;
do not replace unrelated receipt APIs or entire source files with newer versions.
Revalidate that revision's own suite and an external lock-contention test before
enabling `cooperative_writers`. Existing in-memory Python imports require session
restart or remain unguarded; their live task CWD continues to block sync safely.
