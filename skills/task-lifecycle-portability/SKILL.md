---
author: Hermes Agent
category: software-development
description: Export, import, and rebuild self-contained task snapshots without mirrors or symlinks.
license: MIT
metadata:
  hermes:
    scenes: [hermes, devops]
    tags: [task-framework, portability, export, import, snapshots, recovery]
    relations:
    - type: depends_on
      target: task-artifact-integrity
      properties: {reason: snapshots must preserve and verify the complete task closure, strength: strong}
name: task-lifecycle-portability
platforms: [linux, macos]
version: 2.0.0
---

# Task Lifecycle Portability

Owns one-task snapshot transport. Task creation, status, rename, retirement, and deletion belong to the lifecycle layer; damaged-file reconstruction belongs to `task-lifecycle-edge-cases`.

## Storage contract

The task directory is the only source of truth. Canonical files are real files; there is no per-profile/per-hash mirror, symlink protection, or relink command.

- `input/` contains source material and is never cleaned.
- `output/` contains generated evidence and is cleared only by explicit hard reset.
- Root MEMORY/CHANGELOG and `memories/` are persistent context.

## Commands

From the task-framework skill directory:

```bash
python3 scripts/manage_task.py export <hash-or-dir>
python3 scripts/manage_task.py import <archive.tar.gz-or-zip>
python3 scripts/manage_task.py rebuild <hash>
```

## Export contract

Current export creates a self-contained tar.gz beside the task directory and includes the complete task except `.git`, including `input/`, `output/`, scripts, metadata, and hierarchical context. Complete evidence is the safe default; output exclusion requires a future explicit, tested option and is not implied.

Before reporting export success:

1. Run task artifact audit.
2. Confirm archive members are contained under one task directory.
3. Confirm canonical files and context pairs are present.
4. Record archive path and checksum.

## Import/rebuild contract

- Accept tar.gz or zip only after archive path traversal checks.
- Refuse overwrite when the destination task exists.
- Restore real files, never symlinks or mirrors.
- Verify task identity/hash and complete context after extraction.
- Regenerate indexes after successful import.

`rebuild` locates a matching snapshot and delegates to import. Ambiguous snapshots must be reported rather than silently selecting the wrong task.

## Cross-machine choice

Use this skill for one-task/offline transfer. Use `task-cross-machine-sync` for an explicitly configured shared Git task root.

See `references/output-model-design.md` for the canonical input/output boundary.
