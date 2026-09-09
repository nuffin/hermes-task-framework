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
│   ├── docs/                 # reports and generated documents
│   ├── logs/                 # execution and diagnostics logs
│   └── deliveries/           # the ONLY external-delivery root
│       └── <bundle>/         # one sendable package: artifacts, docs, SHA256SUMS
└── scripts/                  # task-owned reusable execution/verification
```

Canonical files are real files in the task directory. There is no mirror directory, metadata symlink, or relink operation.

## Delivery package contract

`output/deliveries/` is the sole root for artifacts intended for external delivery. A task has one sendable package at `output/deliveries/<bundle>/`; final binaries, documents, attachments, and any toolchain-specific candidate artifacts live inside that bundle. The bundle root owns an aggregate `SHA256SUMS`; nested candidate packages may additionally own their own checksums.

Do not create `output/deliverables/` or another sibling delivery root. If a new package archive is produced after an earlier archive, retain the prior archive and use an incrementing `.revN.zip` filename for the new one.

## Cleanup

- Hard reset removes and recreates only `output/`, resets non-DONE checkboxes, and preserves input/context/metadata/scripts.
- Pipelines write generated specifications and phase outputs under `output/`.
- Never use exclusion-based deletion at task root.

## Snapshot

A full portability snapshot includes input, output, scripts, metadata, and context unless an explicit future option defines and verifies a narrower contract.
