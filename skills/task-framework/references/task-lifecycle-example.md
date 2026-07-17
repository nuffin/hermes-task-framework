# Task Lifecycle Walkthrough

This example traces a paper-reproduction task from creation through completion.

## 1. Create

For code/tool tasks, create logs/ only:

```
ts=$(date '+%Y%m%d-%H%M%S')
mkdir -p "tasks/${ts}.paper-reproduction/logs/"
```

For research/documentation tasks, also create docs/:

```
ts=$(date '+%Y%m%d-%H%M%S')
mkdir -p "tasks/${ts}.kangyang-center-research/logs/"
mkdir -p "tasks/${ts}.kangyang-center-research/docs/"
```

Result: `tasks/20260601-164001.paper-reproduction/` (code) or
         `tasks/20260602-041236.kangyang-center-research/` (research)

## 2. Status — active

TASK.md starts with:

```markdown
## Status

active — running pre-checks
```

## 3. Pre-checks (optional)

Present when uncertainty exists:

```markdown
## Pre-checks

- [ ] Can DeepSeek API replace GPT-4?
- [ ] Can uv replace conda?
```

Agent:
1. Reads Pre-checks section
2. For each `[ ]`, researches and writes `logs/precheck.YYYYMMDD-HHMMSS.md`
3. Marks `[ ]` → `[x] conclusion`
4. When all done, presents summary and pauses for user confirmation

After confirmation, `## Pre-checks` section is typically kept with `[x]` items (history) or deleted entirely.

## Checklist with BREAK

```markdown
## Checklist

- [x] Phase 1 — Environment setup          ← already done
- [ ] Phase 2 — Run experiments
- [ ] BREAK: Check initial results before proceeding
- [ ] Phase 3 — Verify against paper
```

Agent iterates:
- `[x]` → skip
- `[ ] Phase 1` → skip (already checked)
- `[ ] Phase 2` → execute, then continue
- `[ ] BREAK: ...` → stop, output summary + message, wait for user

## 5. User confirms BREAK

Agent rewrites TASK.md:

```markdown
- [x] DONE: Check initial results before proceeding
- [ ] Phase 3 — Verify against paper
```

Execution resumes on next `task_run`.

## 6. Completion

When all `[ ]` are `[x]`, the agent sets:

```markdown
## Status

completed — all phases done, ASR matches paper
```

## Directory structure at end

For a **code/tool task** (paper reproduction):

```
tasks/
└── 20260601-164001.paper-reproduction/
    ├── README.md
    ├── TASK.md
    └── logs/
        ├── precheck.20260601-164001.md
        ├── output.20260601-164500.log
        ├── error.20260601-164500.log
        ├── output.20260601-171200.log
        └── error.20260601-171200.log
```

For a **research/documentation task** (康养中心调研):

```
tasks/
└── 20260602-041236.kangyang-center-research/
    ├── README.md              ← overview + key findings summary
    ├── TASK.md                ← checklist (Phase 1-5)
    ├── docs/                  ← organized markdown research materials
    │   ├── paper-summaries.md
    │   ├── product-categories.md
    │   └── architecture-proposal.md
    └── logs/
        └── summary.20260602-120000.log
```
