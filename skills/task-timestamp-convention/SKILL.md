---
author: Hermes Agent
category: software-development
description: 'Task directory naming conventions — timestamp format (local timezone)
  AND name content guidelines. Name must be self-explanatory: <system/domain>-<deliverable-type>
  not generic terms.'
license: MIT
metadata:
  hermes:
    relations:
    - properties:
        reason: Called during every task_create
        strength: strong
      target: task-framework
      type: used_in_workflow
    scenes:
    - hermes
    tags:
    - task-management
    - naming-convention
    - timestamp
    - hermes
    - directory
    - workflow
name: task-timestamp-convention
platforms:
- linux
- macos
version: 1.1.0
---

# Task Naming Conventions

Two aspects: **timestamp format** and **name content**.

## 1. Timestamp: Local Timezone

When creating task directories, the timestamp must use **local time** (UTC+8), **not UTC**.

```bash
# ✅ CORRECT — local timezone
TS=$(date +"%Y%m%d-%H%M%S")

# ❌ WRONG — UTC (off by 8 hours)
TS=$(date -u +"%Y%m%d-%H%M%S")
```

## 2. Name: Self-Explanatory Content

The task name (after the timestamp) must describe **what system/domain** and **what deliverable type**. Generic terms like "architecture-diagram", "analysis", "research" alone are not acceptable.

### Pattern

```
<system-or-domain>-<deliverable-type>
```

### Good vs Bad Examples

| ❌ Bad (too generic) | ✅ Good (self-explanatory) |
|---------------------|--------------------------|
| `system-architecture-diagram` | `<system-name>-architecture` |
| `api-design` | `eir-health-data-api-design` |
| `bug-fix` | `user-service-login-500-error-fix` |
| `code-review` | `heart-health-backend-PR-42-review` |
| `research` | `memory-retrieval-trigger-mechanisms-research` |

### Why

Task names appear in `tasks/` directory listing, `tasks/README.md` index, and kanban cards. A name like `system-architecture-diagram` could mean any system — the agent and user must click into TASK.md to understand what task it is.

### Exceptions

Simple one-off actions that live in the task root for <24h may use short names. Anything expected to persist longer must follow the pattern above.

## 3. Related

- task-framework — parent skill governing task creation lifecycle
- workflow-conditional-branching — decision-fork pattern for multi-phase tasks
