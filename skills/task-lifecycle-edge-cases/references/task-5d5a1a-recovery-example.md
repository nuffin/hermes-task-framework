# Task recovery evidence example

A task was found without a usable TASK.md after an unsafe cleanup.

## Evidence used

1. `.hermes-task.json` established identity, outputs, and relationships.
2. Root MEMORY and CHANGELOG established durable facts and chronological state.
3. `input/`, `output/`, and scripts established available source and generated evidence.
4. The governing task type/skill supplied the valid phase structure.
5. Only phases with matching artifacts and verification were marked complete.

## Recovery result

- Canonical TASK.md was reconstructed as a real file in the task root.
- Missing MEMORY/CHANGELOG files were restored according to compact-directory-memory.
- Hierarchical subsystem pairs were verified when present.
- Indexes were regenerated.
- No mirror, symlink, relink, or profile-local task copy was created.
