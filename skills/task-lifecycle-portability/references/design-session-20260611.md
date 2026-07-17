# Session Design Notes: Task Portability

From a session with Hauzer on 2026-06-11 discussing TASK.md loss and recovery architecture.

## Problem

Pipeline exclusion-based deletion (`rm -rf tts-*/ RECORDING.md ...` or `find . -not -name 'REQUIREMENTS.md' -delete`) destroyed TASK.md because it was a regular file in the task root. User observed: "你那次是排除式删除，把除了 REQUIREMENTS.md 之外的很多有用的文件都删光了."

## Solution Architecture (agreed design)

Three-layer protection:

1. **Directory isolation** — input/ (source) + output/ (generated) boundary. Pipeline only touches output/. Never exclusion-based deletion at task root.

2. **Symlink protection** — TASK.md, TASK_MEMORY.md, .hermes-task.json all symlink to `~/.hermes/personal/tasks/<hash>/`. rm -rf task dir only breaks symlinks; actual content survives.

3. **Tar.gz portability** — `manage.py export` creates self-contained snapshot with resolved content (no symlinks in archive), both git repos preserved. `import` restores symlinks on target machine.

## Key Decisions

- output/ excluded from tar.gz (regenerable)
- tar.gz committed to git (storage cost accepted)
- Cross-machine: no merge, independent tasks. Manual fusion via ref: links.
- `~/.hermes/personal/tasks/<hash>/` git can bare-run (no upstream). Metadata tracking > remote collaboration.
- Old tasks: migrate if feasible, abandon if not.

## Manage.py Split

| Responsibility | Skill | Commands |
|---|---|---|
| Note-taking (observer, file-agnostic) | task-memory | append, read |
| Lifecycle (orchestrator, manages locations) | task-framework | init, relink, export, import, rebuild, reindex |
