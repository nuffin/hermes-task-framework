# TASK.md Format Validation Checklist

Systematic checklist for validating a TASK.md against the `project-tasks` skill spec.

## Section Checklist

- [ ] **`# Task: <Name>`** — Title matches the task directory name (after the timestamp prefix)
- [ ] **`## Status`** — Header present. Next line is `active | paused | completed | cancelled — <reason>`. Parsable by `grep -m1 '^## Status'`
- [ ] **`## Goal`** — Single one-liner describing what the task achieves
- [ ] **`## Pre-checks`** — Section name is EXACTLY `## Pre-checks` (not `Pre-check results`, `Pre-checks (executed X)`, etc.). The executor checks for this exact string. If the section exists, checkboxes follow directly under it (not under a subheading like `### 待决策事项`)
- [ ] **`## 环境要求`** — Table format with at minimum columns: `项目`, `最低要求`, `说明`. Present when the task has environment dependencies
- [ ] **`## Checklist`** — Phase headings (`### Phase N — ...`) with `[ ]` / `[x]` items. Optional `BREAK:` lines between phases
- [ ] **`## Notes`** — Free-form section at the bottom. Contains decisions, reference links, or research summaries that don't belong in Pre-checks

## Common Deviations (check for these)

| Deviation | Fix |
|-----------|-----|
| `## Pre-check results` or `## Pre-checks results` | Rename to `## Pre-checks` |
| Pre-check checkbox items under a subheading (`### 待决策事项`) | Move checkboxes directly under `## Pre-checks` |
| Research notes/results inline in Pre-checks section | Move detailed findings to `## Notes`; keep Pre-checks as compact checkboxes only |
| Stray table-syntax artifacts (`|## Pre-checks`) | Remove leading `|` and trailing `|` from section headers |
| Status line missing the dash format | Rewrite as `active — <reason>` (space, em-dash, space) |
| `BREAK:` line inside a code block | BREAK must be unformatted markdown text, not inside backticks |
| No `## 环境要求` when task needs specific tools/API keys/env vars | Add the table with accurate minimum requirements |
