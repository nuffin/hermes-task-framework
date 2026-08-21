---
author: Hauzer
category: software-development
description: Route facts among global memory, task MEMORY.md, and task CHANGELOG.md.
license: MIT
metadata:
  hermes:
    scenes:
    - hermes
    - coding
    tags:
    - task-framework
    - task-context
    - memory
    - changelog
    - knowledge-management
    relations:
    - type: depends_on
      target: compact-directory-memory
      properties:
        reason: compact-directory-memory owns directory file formats and hierarchy
        strength: strong
    - type: complemented_by
      target: task-framework
      properties:
        reason: task-framework owns task lifecycle and invokes this routing policy
        strength: strong
name: task-context-storage
version: 2.0.0
---

# Task Context Storage

Defines which persistence layer owns each kind of context. File formats, nested directory structure, and maintenance tooling are delegated to `compact-directory-memory`.

## Persistence layers

| Layer | Scope | Content | Read/write timing |
|------|-------|---------|-------------------|
| Global `memory()` | All sessions and tasks | User preferences and stable environment facts | Automatically injected; update sparingly |
| Task `MEMORY.md` | One task or subsystem | Stable expected-state facts and constraints | Read fully before work; update only when facts change |
| Task `CHANGELOG.md` | One task or subsystem | Decisions, operations, observed verification, blockers, next step | Read recent entries before work; append after work |
| Raw logs | One execution | Command output, traces, generated diagnostics | Read as needed; safe to clean according to task rules |

## Route to global memory()

- User identity, durable preferences, and recurring corrections.
- Stable environment facts used across unrelated tasks.
- Cross-task workflow constraints.

Do not store task progress, commits, issue numbers, transient failures, or session outcomes here.

## Route to task MEMORY.md

- Expected configuration and stable conventions.
- Durable paths, interfaces, ports, ownership boundaries, and invariants.
- Facts that another session must know before changing the same task or subsystem.

Do not store momentary runtime status or chronological history here.

## Route to task CHANGELOG.md

- Why one option was chosen over another.
- What was changed and where.
- Real test, build, migration, or health-check results.
- Failures, fixes, unresolved blockers, and exact next step.
- Session and phase outcomes.

## Hierarchical tasks

When a task spans multiple subsystems, load `compact-directory-memory` and use its hierarchical layout. Root files index and synthesize cross-subsystem facts; `memories/<sub-system>/` owns detailed subsystem context.

The routing rule remains unchanged at every level:

- stable expected state → `MEMORY.md`
- chronological observed work → `CHANGELOG.md`

## Boundary cases

When one observation contains both a reusable preference and a task decision, split it:

- global `memory()` receives the durable preference;
- task `CHANGELOG.md` receives the local decision and its consequences;
- task `MEMORY.md` receives only a resulting stable fact, if one exists.

## Relationship to task-framework

`task-framework` should reference this skill for context-routing decisions and `compact-directory-memory` for concrete directory management. It should not duplicate either skill's detailed rules.
