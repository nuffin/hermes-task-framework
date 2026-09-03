---
name: task-requirement-intake
description: "Use when execution discovers requirements. Route TODOs."
version: 1.0.0
author: Hermes Agent
license: MIT
category: hermes
metadata:
  hermes:
    scenes: [hermes, common]
    tags: [task-framework, requirements, TODO, routing, lifecycle, subtasks]
---

# Task Requirement Intake

This skill owns the `TASK.md` `## TODO` lifecycle. A TODO is an
undecomposed requirement discovered during execution, not a checklist phase.
Intake it before deciding how it affects the current task.

## Record

Add a row to the parent's TODO table with all of:

- stable row ID;
- requirement text;
- source (phase, post-flight, user, review, or other evidence);
- local timestamp;
- status (`open`, `decomposed`, `routed`, `cancelled`, or `blocked`);
- scope decision (`open`, `continuous`, `nested`, `top-level`, `cancelled`, or `blocked`);
- outcome/reference (checklist phase, child task path, independent task path, cancellation reason, or blocker).

Use `../task-framework/scripts/todo_lifecycle.py` to update rows. Do not
silently turn a TODO into a completed checklist item or omit it from TASK.md.

## Classification points

Run classification at intake, post-flight, and every phase transition:

1. **continuous** — progressive/continuous with existing checklist work.
   Append or refine checklist phases. Mark `decomposed` and record the phases.
2. **nested** — strongly related but independently lifecycle-deliverable and
   not fully overlapping the parent. Create a first-class child through
   `manage_task.py create <name> --parent <parent>`. Mark `routed` and record
   the child path/hash.
3. **top-level** — unrelated to the parent. Create an independent top-level
   task with the normal lifecycle. Mark `routed` and record its path/hash.

A TODO reaches a terminal state only when decomposed into checklist work,
routed to a nested/top-level task, explicitly cancelled, or explicitly blocked
with a reason. `open` means unresolved and prevents claiming the task complete.

## Continuation loop (optional, for orchestrated L1 execution)

When an L1 worker returns, L0 performs **one** reconciliation before selecting
more work. Pass a stable `result_id` and any newly discovered requirements to
`todo_lifecycle.reconcile_return()` (or `task_api.py reconcile`). The function
records the result ID, so retries return `IDEMPOTENT` and never duplicate TODO
rows, checklist phases, or routes.

The returned outcome is explicit:

- `CONTINUE` — route list contains newly classified continuous/nested/top-level work;
- `CONTINUE_WAITING` — TODOs exist but their declared `depends_on` phases are not ready;
- `COMPLETE` — no open TODO remains and no route is pending;
- `HARD_BLOCK` — the worker reported a genuine blocker or decision boundary;
- `IDEMPOTENT` — this result was already reconciled.

Only dependency-ready items may be routed. Continuous work is appended to the
current checklist; nested and top-level items are handed to their respective
task lifecycle. A missing safe default, destructive action, or hard tool block
must stop the loop rather than trigger an automatic dispatch. Continue invoking
the same protocol after each returned L1 result until `COMPLETE` or
`HARD_BLOCK`; never spin without a new result.


Before completing the parent task, call `todo_lifecycle.validate_todos()`.
The task API exposes `todos` and `todo_validation_errors`; `TASKS.md` displays
TODO status and outcomes separately from checklist progress.
