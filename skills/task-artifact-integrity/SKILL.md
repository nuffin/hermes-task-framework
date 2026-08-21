---
author: Hermes Agent
category: software-development
description: Validate task context closure, artifacts, references, and safe relocation before continuation or deletion.
license: MIT
metadata:
  hermes:
    scenes: [hermes, coding, research]
    tags: [task-framework, artifact-integrity, relocation, audit, task-recovery]
    relations:
    - type: depends_on
      target: task-framework
      properties: {reason: task-framework defines canonical task files and references, strength: strong}
    - type: complemented_by
      target: compact-directory-memory
      properties: {reason: hierarchical context files are part of task closure, strength: strong}
name: task-artifact-integrity
platforms: [linux, macos]
version: 2.0.0
---

# Task Artifact Integrity

Use when relocating a task root, consolidating related tasks, diagnosing an apparently empty task, or validating that another session can continue safely.

## Context closure

A complete task closure includes:

- `TASK.md`, `README.md`, `MEMORY.md`, `CHANGELOG.md`, `.hermes-task.json`;
- `memories/<sub-system>/MEMORY.md` and `CHANGELOG.md` pairs when hierarchical;
- `input/`, `output/`, and `scripts/` inventories;
- named outputs, dependencies, related/superseded tasks, ticket/project extension fields;
- absolute paths and cross-task references.

## Inspection

1. Resolve the task through `task_api.py describe`.
2. Read root and target subsystem context.
3. Inventory source inputs separately from generated output.
4. Resolve every related task and named output.
5. Report missing, empty, stale, or external references before mutation.

## Safe relocation

1. Confirm exact source and destination roots.
2. Refuse overwrite when destination exists.
3. Copy metadata-preserving content without `--delete`.
4. Compare relative path, type, size, and SHA-256 manifests.
5. Rewrite absolute references only after copy verification.
6. Append relocation entries to affected CHANGELOG files.
7. Regenerate both roots' indexes.
8. Remove source only after equality and reference verification.

Same-machine relocation needs no archive unless requested. Cross-machine transfer or explicit rollback may retain an archive.

## Completion evidence

Report task hashes, roots, input/output inventories, manifest equality, context-pair verification, rewritten references, index regeneration, and source/archive status.

See `references/task-root-relocation.md` for the checklist.

## Permanent tooling

```bash
python3 scripts/task_integrity.py audit <hash-or-dir>
python3 scripts/task_integrity.py closure <hash-or-dir>
python3 scripts/task_integrity.py manifest <hash-or-dir> --output <manifest.json>
python3 scripts/task_integrity.py compare <source-dir> <destination-dir>
```

All commands emit JSON and return nonzero when integrity or equality fails.
