# Task root relocation checklist

## Invariant

After relocation, canonical files, root and subsystem context, source inputs, generated evidence, named outputs, and related-task references remain resolvable without an undeclared old root.

## Required checks

| Check | Evidence | Failure response |
|---|---|---|
| Canonical files | TASK, README, MEMORY, CHANGELOG, metadata are nonempty | Restore/report before source deletion |
| Hierarchical context | Every subsystem directory has both context files | Repair complete pair before relocation |
| Source input | `input/` inventory | Locate source owners; never infer emptiness is acceptable |
| Generated evidence | `output/` and review/log inventory | Preserve evidence or owning task |
| Related closure | metadata and document references resolve | Move closure or rewrite verified references |
| Named outputs | every registered output resolves | Repair metadata/path before completion |
| Copy equality | relative path/type/size/SHA-256 manifests match | Retain source and fail relocation |
| Indexes | destination and source indexes regenerated | Do not report completion |

## Record

```markdown
## YYYY-MM-DD HH:MM:SS TZ

**Operation:** Relocated task `<hash>` from `<old-root>` to `<new-root>`.
**Context closure:** `<related hashes and subsystems>`.
**Verification:** `<file count and manifest equality>`.
**References:** `<updated paths or none>`.
**Indexes:** `<old/new regeneration result>`.
**Source status:** `<removed after verification / retained>`.
```
