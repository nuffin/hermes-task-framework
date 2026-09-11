---
name: task-root-git-operations
description: "Use when manually committing, rebasing, or pushing a shared task root. Preserve every task's working state."
version: 1.0.0
author: Hermes Agent
license: MIT
category: software-development
metadata:
  hermes:
    scenes: [hermes, coding, devops]
    tags: [task-framework, git, shared-root, commit, rebase, push, worktree]
    relations:
      - type: depends_on
        target: task-cross-machine-sync
        properties:
          reason: "The sync skill owns automated transactions; this skill owns the manual shared-root workflow."
          strength: strong
      - type: complemented_by
        target: task-lifecycle-discipline
        properties:
          reason: "Task lifecycle operations remain task-framework-owned."
          strength: medium
platforms: [linux, macos]
---

# Task Root Git Operations

Use this skill only for manual Git operations in the configured
`$HERMES_TASKS_ROOT` repository. It protects the shared root from one task's
Git operation moving, hiding, committing, or discarding another task's work.

For unattended or cross-machine checkpoint synchronization, use
`task-cross-machine-sync` instead. For a normal standalone repository, use its
project-specific Git workflow rather than this skill.

## Non-negotiable shared-root boundary

`$HERMES_TASKS_ROOT` is a multi-task shared worktree. Do not treat it as a
single-task checkout.

Never run any of these commands in the shared task root:

```text
git stash
git stash push
git stash pop
git stash drop
git reset --hard
git clean
git checkout -- .
git restore .
```

Do not use a root-wide `git add -A`, `git commit`, `git pull --rebase`, or
`git rebase` while another task's changes are staged, unstaged, or untracked.

If a task root already contains historical stash entries, inspect and recover
or discard them only through the controlled procedure in
[Historical stash recovery](#historical-stash-recovery). The prohibition above
exists because a shared-root stash can hide work owned by another active task.

## Required operation order

For every independently authorized task group, the order is fixed:

```text
1. Commit the exact task directory.
2. Pull/rebase against the authorized remote branch.
3. Push the rebased commit.
4. Read back the exact remote ref.
```

Do not push a task commit before checking the remote branch after the commit.
Do not replace step 2 with a blind push and repair a rejection later.

## Preflight: inventory and partition

Before any mutation:

1. Resolve the canonical task root with task-framework.
2. Read `git status --short`, current branch, remotes, and
   `origin/<branch>...HEAD` divergence.
3. Enumerate every staged path and every unstaged/untracked path separately.
4. Partition paths by their first task-directory segment:

   ```text
   YYYYMMDD-HHMMSS.<name>-<hash6>/
   ```

   Keep root `README.md`, root `TASKS.md`, `inbox/`, `declined/`, and any other
   root-level path as independent groups. Never attach a root index to an
   arbitrary task commit merely to make a commit succeed.
5. Read the target task's `TASK.md`, `MEMORY.md`, and recent `CHANGELOG.md`
   before deciding its commit message or whether an artifact is meaningful.

When the user says “all staged tasks, one task at a time”, enumerate all staged
path groups and process every group. Do not silently exclude logs, generated
artifacts, or a task whose scope is unfamiliar.

## Exact task commit

For one task directory `TASK_DIR`:

```bash
git add -A -- "$TASK_DIR"
git diff --cached --name-only -- "$TASK_DIR"
git diff --cached --check -- "$TASK_DIR"
git commit --only -S -m "<conventional message>" -- "$TASK_DIR"
```

Read back the committed path list with:

```bash
git diff-tree --no-commit-id --name-only -r HEAD
```

It must contain only the declared task directory. If a raw evidence artifact
contains meaningful CRLF, terminal control bytes, or trailing spaces,
classify the `git diff --check` finding as evidence-format preservation before
committing; never mutate raw logs merely to silence the check. Record the
exception in the task's CHANGELOG or delivery report.

## Rebase without disturbing active tasks

### Clean shared root

If the shared root is clean after the exact task commit, run:

```bash
git pull --rebase <remote> <branch>
```

Inspect the result. Resolve only a verified semantic conflict; use
`GIT_EDITOR=true git rebase --continue`, then inspect the resulting commit,
conflict markers, status, and relevant task files.

### Dirty shared root or root-index conflict

If any other task has staged, unstaged, or untracked paths, do not stash it and
do not run rebase in the shared root. Create an isolated worktree from the
post-commit task-root HEAD:

```bash
git worktree add -b sync/<task-hash>-<timestamp> <temporary-worktree> HEAD
cd <temporary-worktree>
git fetch <remote> <branch>
git rebase <remote>/<branch>
```

Rules for the isolated worktree:

- Its branch is temporary transport state, not a task branch.
- A conflict in task content stops for semantic resolution.
- A conflict in generated root `README.md` or `TASKS.md` may keep the verified
  remote version only when the local conflicting commit is an equivalent stale
  index refresh. Regenerate indexes after integration if the task framework
  requires it; do not discard a task-content conflict as an index conflict.
- Verify the exact task commit remains in the rebased history and its path list
  still contains only its declared task directory.
- Never force-push to compensate for a local rebase.

## Push and read-back

Push only after explicit authorization for the named remote and branch:

```bash
git push <remote> HEAD:<branch>
local_head=$(git rev-parse HEAD)
remote_head=$(git ls-remote <remote> "refs/heads/<branch>" | cut -f1)
test "$local_head" = "$remote_head"
```

After each push, re-scan the shared root for newly staged groups before handling
another task. A concurrent writer can add a new task while a prior task is
being published.

Do not infer that a remote named `origin` is the correct destination when the
repository policy or explicit user instruction names a different destination.
Never force-push without a separate explicit authorization.

## Historical stash recovery

Historical stashes may predate this skill. Recover them without disturbing the
shared root:

1. Record stable stash object IDs with `git rev-parse stash@{N}` before any
   mutation; numbered selectors shift after a drop.
2. Inspect every stash with `git stash show --include-untracked --stat` and
   `--name-status`.
3. Compare stashed blobs against current `HEAD` by task group. A path that is
   byte-identical or superseded by a later verified task artifact is not useful.
4. Create an isolated audit worktree at current `HEAD`; run
   `git stash apply --index <stable-stash-id>` only there.
5. For useful content, merge only the missing task-owned facts or artifacts
   into the shared root by exact task path, then make a dedicated task commit,
   rebase, push if authorized, and verify the remote ref.
6. Do not use `git stash pop` in the shared root. After every useful fragment
   is committed or every path is proven superseded, drop the audited stash by
   stable object ID or deepest numbered selector first.

A stash conflict in a task `CHANGELOG.md` normally means later entries exist.
Preserve a historically meaningful missing entry by appending it chronologically;
do not replace later entries with the stash version.

## Completion evidence

For every task group report:

- staged and committed path count;
- commit SHA and signature result;
- rebase target and any conflict treatment;
- remote ref SHA after push, when push was authorized;
- remaining shared-root staged/unstaged/untracked group counts;
- any untouched historical stash or a reason it was dropped.

## Common failures

| Failure | Required response |
|---|---|
| `git push` rejected because remote advanced | Fetch/rebase before retrying; use an isolated worktree if the shared root is not clean. |
| A normal `git commit` includes another task's staged paths | Do not push. Rebuild the commit with exact path scoping before publication. |
| `git diff --check` flags archived raw logs | Preserve evidence bytes; document the exception instead of rewriting history. |
| A stash contains multiple tasks | Audit in an isolated worktree and recover only useful task-owned fragments. |
| Root index conflicts during rebase | Distinguish stale generated index content from task content; never discard task facts as a root-index shortcut. |
| Existing task changes make a root rebase unsafe | Leave them in place and use an isolated worktree; never stash or clean the shared root. |
