# Task Overview Discovery

When asked to list or update a summary of all tasks, use this approach rather than relying on a potentially stale root README.md.

## Approach

1. Scan the `tasks/` directory for subdirectories matching `YYYYMMDD-HHMMSS.*` pattern
2. For each, read the `README.md` to extract:
   - **Title** (`# Title` — first H1)
   - **Description** (first line after H1)
   - **Status** (`## Status` section or inline mention)
3. Present a compact table to the user

## Fallback When README.md is Empty

If a task directory has no README.md, check for `TASK.md` and extract the first H1 and status section.

## Index File Maintenance

The root `tasks/README.md` is the canonical index. After any read/update, regenerate it with the `update-task-index` script from the skill's SKILL.md.

## Output Format

Prefer a compact pipe-delimited table for terminal readability:

```
| Directory | Title | Status | Description |
|-----------+-------+--------+-------------|
```

Avoid bullet lists or verbose paragraphs for listing purposes.
