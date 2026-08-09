# Session Design Notes: Task Portability

Session notes (2026-06-11) discussing TASK.md loss and recovery architecture.

## Problem

Pipeline exclusion-based deletion (`rm -rf tts-*/ RECORDING.md ...` or `find . -not -name 'REQUIREMENTS.md' -delete`) destroyed TASK.md because it was a regular file in the task root. The root cause was exclusion-based deletion catching all non-protected files.

## Solution Architecture (agreed design)

Three-layer protection:

1. **Directory isolation** — input/ (source) + output/ (generated) boundary. Pipeline only touches output/. Never exclusion-based deletion at task root.

2. **File protection** — TASK.md, CHANGELOG.md, .hermes-task.json all live directly in the task directory. Files are the single source of truth.

3. **Tar.gz portability** — `manage.py export` creates self-contained snapshot with resolved content (no symlinks in archive), both git repos preserved. `import` restores symlinks on target machine.

## Key Decisions

- output/ excluded from tar.gz (regenerable)
- tar.gz committed to git (storage cost accepted)
- Cross-machine: no merge, independent tasks. Manual fusion via ref: links.
- Old tasks: migrate if feasible using `manage_task.py migrate`, abandon if not.

## Manage.py Split

| Responsibility | Skill | Commands |
|---|---|---|
| Note-taking (observer, file-agnostic) | task-memory | append, read |
| Lifecycle (orchestrator, manages locations) | task-framework | init, relink, export, import, rebuild, reindex |
