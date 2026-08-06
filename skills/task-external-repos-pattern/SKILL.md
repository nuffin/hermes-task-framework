---
author: Hermes Agent
category: software-development
description: Documentation for the repos/ directory pattern — cloning external git
  repos into a task for analysis, audit, or code extraction. Defines cleanup semantics,
  directory structure, and pitfall avoidance.
license: MIT
metadata:
  hermes:
    scenes:
    - research
    - coding
    tags:
    - git
    - repos
    - clone
    - analysis
    - audit
    - task
    - software-development
name: task-external-repos-pattern
tags:
- task
- repos
- git
- clone
- analysis
- external
version: 1.0.0
---

# External Repositories in Tasks (repos/ Pattern)

## When to Use

When a task needs to clone one or more external git repositories for analysis, auditing, or code extraction. Common scenarios:

- **Research task** — clone a list of repos from an awesome-list to study their structure
- **Audit task** — clone a repo to analyze its codebase, commit history, or architecture
- **Integration task** — clone dependencies to understand their API surface
- **Migration tasks** — clone source repos as input material for migration scripts

## Directory Convention

Place cloned repos in a top-level `repos/` directory inside the task:

```
tasks/<ts>.<name>-<hash6>/
├── input/                 ← inbox source files (PDFs, REQUIREMENTS.md)
├── output/                ← generated files (reports, docs, logs)
│   ├── docs/
│   └── logs/
├── repos/                 ← *** cloned external git repos ***
│   ├── repo-name-1/
│   ├── repo-name-2/
│   └── ...
├── scripts/
├── TASK.md
├── README.md
└── .hermes-task.json
```

## Semantics: repos/ vs input/ vs output/

| Directory | Nature | `task_reset --hard` | Example content |
|-----------|--------|---------------------|-----------------|
| `input/` | Source materials (copied from inbox) | ❌ Never deleted | PDFs, REQUIREMENTS.md, images |
| `output/` | Generated artifacts | ✅ **Deleted** | Reports, logs, compiled files |
| `repos/` | External git clones (not inbox, not generated) | ❌ Never deleted | Cloned `.git/` trees |

**Key rule:** `repos/` is treated like `input/` — never deleted by cleanup operations. When `scripts/clean.sh` exists in the task, it explicitly declares `repos/` as PRESERVED. When no clean.sh exists, `task_reset --hard` still only touches `output/`, so repos/ survives regardless — but adding an explicit clean.sh makes the intent auditable.

## How to Add repos/ to a Task

During task creation:

```bash
mkdir -p tasks/<ts>.<name>-<hash6>/{input,output/docs,output/logs,repos,scripts}
```

Clone each target repo into `repos/`:

```bash
cd tasks/<ts>.<name>-<hash6>/repos
git clone https://github.com/owner/repo-name.git
```

For large repos where full history isn't needed:

```bash
git clone --depth 1 https://github.com/owner/repo-name.git
```

## How to Reference repos in TASK.md

In the Data Flow table:

```markdown
## Data Flow

| 文件 | 来源 | 用途 | 格式说明 |
|------|------|------|---------|
| `repos/owner-repo/README.md` | 外部克隆 | 分析项目结构 | 标准 markdown |
```

In the checklist:

```markdown
- [ ] Phase 2 — Clone repos to repos/
- [ ] Phase 3 — Analyze repos/ structure
```

## Cleanup Considerations

- `repos/` is NOT cleaned by `task_reset --hard`. To reclone (stale repos), do so manually or via a dedicated Phase.
- Cloned repos retain their `.git/` directories — `git pull` is sufficient to update without a full reclone.
- Add a `## 环境要求` note to TASK.md for large repos that consume significant disk space.

## Pitfalls

- **Don't put cloned repos in `output/`** — they'd be wiped by `task_reset --hard`, losing `.git/` history and requiring a full reclone.
- **Don't put them in `input/`** — `input/` is for inbox-sourced files (PDFs, REQUIREMENTS.md). Cloned repos are a different category.
- **Beware submodules** — use `git clone --recursive` if the repo uses submodules; expect larger clones.
- **Disk space** — for massive repos (OSSU CS at GBs, dotnet docs), consider `--depth 1` shallow clone unless full history is needed.
- **Path length on Windows/WSL** — very deep paths in cloned repos may cause issues under WSL. Keep task names short enough.

## Relation to Task-Framework

This pattern extends the `task-framework` skill's directory structure. The `task-framework` SKILL.md now lists `repos/` in its canonical directory tree and documents the `scripts/clean.sh` custom cleanup mechanism.

For `task_reset --hard` semantics: `repos/` is never deleted by cleanup operations (same as `input/`). Custom `clean.sh` scripts can further refine which directories to protect.

## Kanban Escalation: Multi-Repo Tasks → Kanban

When a task involves **multiple independent external repos** (e.g. cloning 5+ repos from an awesome-list for study), the work typically decomposes into parallel workstreams. The user's convention is **one kanban card per task-framework task** (not one card per sub-operation):

User signal: *"一个 clone 任务创建一个 card"* / *"这是多个任务了，放到 default 看板里"*

**Right approach:**
1. Create a single task-framework task with its own `repos/` directory
2. Create one kanban card for that task, `--workspace dir:<task-path>`
3. Update the bridge db.yaml to map task hash ↔ card id

**Wrong approach:**
- Creating one kanban card per individual sub-repo
- Mixing unrelated work into one card

See also: `kanban-orchestrator` skill for decomposition playbook, `kanban-bridge` for task ↔ card mapping.

## Custom Clean Methods (Implemented)

Each task can protect sensitive directories from cleanup via a `scripts/clean.sh` script:

**查找顺序（由 `task_reset --hard` 执行）：**
1. 检查 `tasks/<ts>.<name>-<hash6>/scripts/clean.sh` — 存在则执行它（替代默认行为）
2. 不存在 → 回退到默认 `rm -rf output/`

**clean.sh 模板：**

```bash
#!/usr/bin/env bash
set -euo pipefail
TASK_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# 明确声明要保留的路径
echo "[clean] repos/ — PRESERVED (cloned repos)"
echo "[clean] input/ — PRESERVED (source materials)"

# 只清理 output/
rm -rf "$TASK_DIR/output"
mkdir -p "$TASK_DIR/output"/{docs,logs}
echo "[clean] output/ cleaned"
```

**设计原则：**
- clean.sh 只控制"删什么不删什么"，不修改 TASK.md 或状态
- 输出中列出保留路径方便审计
- 没有 clean.sh 时回退到默认行为，不破坏现有任务

**本 task 的 clean.sh 示例路径：**
`tasks/20260615-213922.awesome-obsidian-vaults-cc6b3b/scripts/clean.sh`
该脚本保护 `repos/`、`input/`，只清理 `output/`。

**Framework 集成状态：**
- `task-framework` SKILL.md 已更新，记录了 clean.sh 查找顺序和模板（`~/hermes/skills/software-development/task-framework/SKILL.md` 的 Task Directory Structure 章节）
- `analysis` task-type 生命周期文档也加了自定义清理的提示
