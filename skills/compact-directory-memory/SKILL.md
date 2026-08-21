---
author: Hauzer S. Lee
category: software-development
description: Manage paired MEMORY.md/CHANGELOG.md in flat or nested directory contexts.
license: MIT
metadata:
  hermes:
    scenes:
    - hermes
    - coding
    tags:
    - memory
    - changelog
    - directory-context
    - hierarchical-memory
    - task-framework
    relations:
    - type: complemented_by
      target: task-context-storage
      properties:
        reason: task-context-storage defines which persistence layer owns each fact
        strength: strong
name: compact-directory-memory
platforms:
- linux
- macos
version: 3.0.0
---

# Compact Directory Memory

The authoritative format and maintenance skill for paired `MEMORY.md` and `CHANGELOG.md` files inside projects, tasks, and other directory-managed entities.

`task-framework` decides when task context must be loaded. This skill owns how directory context is structured, formatted, created, read, updated, and verified.

## Context pair

| File | Meaning | Update mode |
|------|---------|-------------|
| `MEMORY.md` | Stable expected-state facts, constraints, paths, interfaces, and conventions | Replace stale facts; keep compact |
| `CHANGELOG.md` | Chronological operations, decisions, verification, failures, and next steps | Append; never rewrite history |

Transient runtime status never belongs in `MEMORY.md`. Record observed execution results in `CHANGELOG.md`.

## MEMORY.md format

```text
<one declarative fact paragraph>

§

<another declarative fact paragraph>

§

🔴 <critical invariant>
```

Rules:

- One fact per paragraph, separated by `§` on its own line.
- No headings, tables, tags, or frontmatter.
- Use declarative facts, not instructions.
- Use `🔴` only for enforced invariants.
- Remove or replace stale facts instead of retaining historical versions.
- Prefer expected configuration over transient observations.
- Keep reusable procedures in skills, not MEMORY.md.

## CHANGELOG.md format

Use chronological entries with the newest entry appended at the bottom:

```markdown
## YYYY-MM-DD HH:MM:SS

**Operation:** What happened.
**Reason:** Why this approach was selected.
**Artifacts:** Files, repositories, or outputs changed.
**Verification:** Commands/checks and real results.
**Blockers:** Unresolved problems, if any.
**Next step:** Exact continuation point for another session.
```

Raw command output belongs in `output/logs/` or another log directory, not in CHANGELOG.md.

## Flat layout

```text
<entity>/
├── MEMORY.md
└── CHANGELOG.md
```

Use for one project, one task, or one cohesive entity.

## Hierarchical layout

Use when multiple sessions modify distinct subsystems under one long-running task or project:

```text
<entity>/
├── MEMORY.md                         # root index and cross-subsystem facts
├── CHANGELOG.md                      # cross-subsystem chronological summaries
└── memories/
    └── <sub-system>/
        ├── MEMORY.md                 # subsystem-owned stable facts
        └── CHANGELOG.md              # subsystem operations and verification
```

Subsystem names are lowercase kebab-case. Every subsystem directory must contain both files.

### Root versus subsystem ownership

- Root `MEMORY.md`: entity identity, subsystem index, cross-subsystem invariants, shared interfaces.
- Root `CHANGELOG.md`: concise cross-subsystem summary with references to affected subsystem logs.
- Subsystem `MEMORY.md`: facts owned only by that subsystem.
- Subsystem `CHANGELOG.md`: detailed work history for that subsystem.

Root files are indexes and syntheses, not copies of subsystem files.

## Read protocol

Before changing a hierarchical entity:

1. Read root `MEMORY.md` completely.
2. Read recent relevant root `CHANGELOG.md` entries.
3. Identify the target subsystem.
4. Read its `MEMORY.md` completely.
5. Read recent relevant entries from its `CHANGELOG.md`.

## Write protocol

After a verified change:

1. Update subsystem `MEMORY.md` only if stable facts changed.
2. Append subsystem `CHANGELOG.md` with operation, reason, artifacts, verification, blockers, and next step.
3. Update root `MEMORY.md` only if the subsystem index or cross-subsystem facts changed.
4. Append a concise root `CHANGELOG.md` summary naming affected subsystem logs.

## Tooling

Create or extend a hierarchical context:

```bash
python3 scripts/manage_directory_context.py init <entity-dir> <sub-system> [<sub-system> ...]
```

Verify required files and naming:

```bash
python3 scripts/manage_directory_context.py verify <entity-dir>
```

The script never overwrites existing context files.

## Relationship to task-framework

`task-framework` owns task creation, status, checklist, indexes, and lifecycle. For task context it must:

1. Create root `MEMORY.md` and `CHANGELOG.md`.
2. Load this skill when hierarchical directory context is requested or detected.
3. Delegate nested creation, format rules, and validation to this skill.
4. Preserve `MEMORY.md`, `CHANGELOG.md`, and `memories/` during reset and cleanup.

## Relationship to changelog skill

The continuous `CHANGELOG.md` in this skill preserves cross-session context. The separate `changelog` skill creates immutable `changelog/<timestamp>.<topic>.md` delivery records. They are complementary and must not replace each other.
