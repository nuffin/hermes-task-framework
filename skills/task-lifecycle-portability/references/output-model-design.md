# Canonical task input/output model

```text
<task>/
├── TASK.md
├── README.md
├── MEMORY.md
├── CHANGELOG.md
├── .hermes-task.json
├── memories/                 # optional hierarchical persistent context
├── input/                    # source material; cleanup must never touch
├── output/                   # generated artifacts; hard reset may clear
└── scripts/                  # task-owned reusable execution/verification
```

Canonical files are real files in the task directory. There is no mirror directory, metadata symlink, or relink operation.

## Cleanup

- Hard reset removes and recreates only `output/`, resets non-DONE checkboxes, and preserves input/context/metadata/scripts.
- Pipelines write generated specifications and phase outputs under `output/`.
- Never use exclusion-based deletion at task root.

## Snapshot

A full portability snapshot includes input, output, scripts, metadata, and context unless an explicit future option defines and verifies a narrower contract.
