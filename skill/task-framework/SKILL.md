---
name: task-framework
description: 'Three-layer task system: (1) methodology — decompose complex work into
  composable operations (info-search, code-write, paper-reproduce…) and composite
  patterns (software-dev, research); (2) container — structured tasks/ directory with
  TASK.md, logs, docs; (3) tooling — reusable scripts for logging, PDF conversion,
  and task execution.'
author: Hauzer S. Lee
license: MIT
category: software-development
platforms:
- linux
- macos
tags:
- task
- methodology
- container
- tooling
- decompose
- operations
- logging
- pdf
version: 1.0.0
metadata:
  hermes:
    tags:
    - docker
    - container
    - logging
    - software-development
---

---

# Task Framework

A three-layer system covering the full task lifecycle:

| Layer | What | Examples |
|-------|------|----------|
| **Methodology** | 如何拆解复杂工作为可组合的操作 | operation catalog (`info-search`, `code-write`…), composite patterns (`software-dev`), decomposition guide |
| **Container** | 如何组织任务的物理文件 | `tasks/<ts>.<name>-<hash6>/` with `TASK.md`, `README.md`, `logs/`, `docs/`, `scripts/` |
| **Tooling** | 执行任务的复用工具 | `scripts/task-runner.sh` (日志封装), `scripts/convert_md_to_pdf.py`, `templates/TASK.md` |

## The Model

A **task** is a goal with structured tracking (directory, checklist, logs).
An **operation** is a unit of work with a defined input, process, and output.
Complex tasks decompose into multiple operations; simple tasks may be a single operation.

```
Task: "复现这篇论文的实验结果"
  └── Operation: paper-reproduce (environment → run → compare)

Task: "开发用户登录功能"
  ├── Operation: info-search        (调研认证方案)
  ├── Operation: code-write         (写后端+前端)
  └── Operation: code-review        (审查)
```

---

## Task Types

每个任务都有**类型**，类型决定了生命周期（创建、执行、清理）和目录结构。类型定义在 `references/task-types/` 下。

### 类型注册表

| 类型 | 说明 | 目录结构 | 生命周期参考 |
|------|------|---------|------------|
| `analysis` | 文档分析/调研：从源文件提取信息，产出分析文档 | `input/`(源文件) + `output/docs/`(产出) | `references/task-types/analysis.md` |
| `external-audit` | 外部项目审计：读取外部路径下的文件，产出分析报告，不复制源文件、不修改外部路径 | `output/docs/`(无 input/) | `references/task-types/external-audit.md` |
| `video-production-pipeline` | 视频生产流水线：根据 REQUIREMENTS.md 自动化录屏配音，由 `video-production-pipeline` skill 驱动 | `input/` (REQUIREMENTS.md + images/) + `output/` (各 phase 目录) | `references/task-types/video-production-pipeline.md` |

### 添加新类型

当发现一种新的任务模式（比如代码开发、数据库迁移等），需要：

1. 在 `references/task-types/` 下创建 `<新类型>.md`
2. 在类型参考中写明完整生命周期：创建 → 执行 → 修改 → 清理 → 完成
3. 更新本注册表，加入新类型
4. 如果新类型需要特殊的 `task_create` 行为，创建 `scripts/create_task.py`（参考 task_create 的 skill 接口）

**生命周期文档模板：**

```markdown
# <类型名> 任务生命周期

## 创建
创建时生成哪些目录和文件？

## 执行
执行时有哪些步骤？产物放在哪？

## 修改
如何安全地修改已有任务？

## 清理
如何清理产物？`task_reset --hard` 做了什么？

## 完成
完成时有什么收尾工作？
```

---

When you receive a task request:
0. **Determine task type** — lookup in the task types registry, load `references/task-types/<type>.md` for lifecycle guidance
1. **Identify the operation pattern** — single-operation or composite? Check the task type's lifecycle doc for the standard workflow
2. **If composite** — break into operations, sequence in TASK.md
3. **For each operation** — follow the standard workflow in its reference
4. **Choose execution strategy** — by complexity

---

## Environment Variables

This skill uses environment variables for portability across machines. After Personal Suite installation, these are set in `~/.hermes/personal/env.sh`:

| Variable | Default | Purpose |
|----------|---------|---------|
| `HERMES_TASKS_ROOT` | `~/studio/hermes/tasks` | Task container root (`tasks/2*/`, `tasks/inbox/`) |
| `HERMES_PROJECTS_ROOT` | `~/studio/hermes/projects` | Project repos root |

**Usage rule:** All inline shell commands in this SKILL.md use `$HERMES_TASKS_ROOT` instead of bare `tasks/` paths. When running commands from a Hermes session, source the env file first:

```bash
source ~/.hermes/personal/env.sh
```

If the variable is unset, fall back to `~/studio/hermes/tasks` (the historical default).

## Task Directory Structure

The canonical tasks root is defined by `$HERMES_TASKS_ROOT` (default: `~/studio/hermes/tasks/`). All relative paths (e.g. `tasks/YYYYMMDD-*`) in documentation are relative to this root. When the user says "tasks" without qualification, this directory is the default reference — not the abstract concept of "任务". "创建一个任务" means creating a `YYYYMMDD-HHMMSS.<name>-<hash6>/` structure here using this skill.

🔴 **Semantic disambiguation (important):** When the user says "任务" or "task", first determine whether they mean (a) a task-framework managed task (in `tasks/YY.../` directories) or (b) a generic concept. Clues: specific name/timestamp, operating on a task directory → (a); abstract discussion → (b). For (a), always use task-framework tools (task_create, task_set_status, etc.) — never raw `mv`/`cp`/`rm` on task directories. For (b), handle as normal conversation.

```\ntasks/\n├── README.md                  ← summary index (directory façade)\n├── TASKS.md                   ← aggregated checklist view (done/total per task)\n├── YYYYMMDD-HHMMSS.<task-name>-<hash6>/\n│   ├── README.md              ← goal, scope, key findings\n│   ├── TASK.md                ← checklist with status + checkboxes\n│   ├── TASK_MEMORY.md          ← per-task memory: auto-appended log of decisions, state, findings\n│   ├── input/                 ← **source files** — NEVER deleted by cleanup operations\n│   │                           (PDF, DOCX, images, REQUIREMENTS.md copied from inbox)\n│   ├── output/                ← **generated files** — CAN be safely deleted entirely\n│   │   ├── docs/              ← analysis documents, reports (for analysis tasks)\n│   │   ├── logs/              ← execution logs\n│   │   ├── tts-<hash6>/       ← pipeline phase dirs (for pipeline tasks)\n│   │   ├── RECORDING.md       ← pipeline generated specs\n│   │   ├── COMPOSITING.md\n│   │   └── ...\n│   ├── inbox/                 ← proposal inbox (one file/dir per idea)\n│   └── declined/              ← rejected proposals (with DECLINED.md)\n```

**`input/` 目录** — 存放从 inbox 复制来的源文件（PDF、DOCX、图片、REQUIREMENTS.md 等）。**核心规则：所有删除操作不得触及 `input/`。**

**`output/` 目录** — 存放所有生成文件（分析文档、执行日志、pipeline 产物如 tts-*/RECORDING.md/COMPOSITING.md 等）。**核心规则：所有删除操作只针对 `output/`。**

`task_reset --hard` 默认清空 `output/`，不动 `input/`。

### 自定义清理脚本

部分 task 有需要特殊保护的目录（如 clone 的仓库、大文件等），可以在 `scripts/clean.sh` 中定义自定义清理行为：

**查找顺序：**
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

**`scripts/task-runner.sh`** 是一个可复用的执行日志封装脚本，使用方式：

```bash
bash scripts/task-runner.sh <task-dir> <command...>
# 自动创建 logs/output.<ts>.log + logs/error.<ts>.log
```

---

## Operation Catalog

Each operation has a reference under `references/operations/<name>.md`.

### Current Operations

| Operation | When to Use | Ref |
|-----------|-------------|-----|
| `file-concat` | 拼接多个源文件为一个 | `references/operations/file-concat.md` |
| `file-convert` | 文件格式转换（docx→md, xlsx→csv, pdf→md） | `references/operations/file-convert.md` |
| `info-search` | 多源信息搜索和抓取（竞品分析、政策调研） | `references/operations/info-search.md` |
| `code-write` | 写代码：单一功能实现，含测试 | `references/operations/code-write.md` |
| `paper-reproduce` | 论文代码复现：环境搭建、跑 pipeline、对比 | `references/operations/paper-reproduce.md` |
| `document-write` | 编写结构化文档（产品需求、产品设计、技术需求、技术设计） | `references/operations/document-write.md` ✅ |
| `code-review` | 代码审查：diff 分析、安全扫描 | `references/operations/code-review.md` |
| `data-analysis` | 数据分析：探索、统计、可视化 | `references/operations/data-analysis.md` |
| `task-overview-discovery` | 扫描 tasks/ 目录、读取 README.md 生成概览表 | `references/task-overview-discovery.md` |
| `web-research` | 网页调研：读取 URL、OCR 截图、生成 summary + discuss | `references/operations/web-research.md` |

New operation types discovered during real tasks should be added here.

---

## Composite Task Patterns

Recurring multi-operation patterns. Each has a reference under `references/composites/<name>.md`.

### Software Development

```
0. [git] Pre-Change Sync → fetch + cherry + ff-only / rebase
1. info-search    → 调研现有方案/技术选型
2. document-write → 写产品需求/产品设计/技术需求/技术设计四份文档
3. code-write     → 实现（TDD）
4. code-review    → 审查
5. [git] Post-Change Workflow → commit → quality-gate → re-sweep
```

Step 0 loads GIT.md's Pre-Change Sync (fetch → cherry → ff-only → rebase → verify).
Step 5 runs GIT.md's Post-Change Workflow (sweep → commit → quality-gate → fix → re-sweep).

Common loops: 需求讨论 (2↔用户), review→fix (3↔4).

### Research Task

For open-ended investigation (competitor analysis, policy study, tech feasibility):

```
1. info-search    → 多源搜索
2. data-analysis  → 整理发现
3. document-write → 写出调研报告
```

### Code Review Session

For a batch review of changes:

```
1. 加载 TASK.md，确认审查范围
2. code-review    → 逐个文件审查
3. document-write → 写 review/SUMMARY.md
4. 更新 TASK.md 状态
```

### Cross-Skill Composite Tasks

Some tasks span multiple tools/skills. For example: generate TTS audio → record browser video → composite audio onto video.

**How composite tasks work:**

1. TASK.md includes a `## Skills` section listing all required skills
2. Each phase in the checklist is prefixed with the skill that handles it
3. Each phase can declare execution mode: default (sequential), `和 Phase X 同步进行` (parallel), or `等待 Phase X 完成` (dependency)
4. When executing, phases run according to their dependency graph
5. Pass outputs between phases (file paths, durations, timestamps)

#### Phase isolation directories

每个 phase 使用独立的子目录，防止文件互相覆盖：

```
tasks/<ts>.<name>-<hash6>/
├── TASK.md
├── RECORDING.md
├── COMPOSITING.md
├── README.md
├── tts-a3f8c2/              ← text-to-speech 的工作目录
│   ├── audio_000001.mp3
│   ├── audio_000002.mp3
│   └── audio_manifest.json
├── recording-bd71ef/        ← browser-video-recording 的工作目录
│   ├── video.mp4
│   └── timeline.txt
├── compositing-c9f3a2/      ← video-audio-compositing 的工作目录
│   └── output.mp4
├── docs/                   ← 共享文档（timestamps.json、多 phase 共用文件等）
└── logs/
```

**规则：**

1. 目录命名：`<short-name>-<hash6>/`，短名用 `-` 连接，尾部加 6 位 hash。不用 `phase_NN_` 前缀，避免步骤顺序变化时目录名需要改动。
2. hash 用随机字符串（如 `a3f8c2`），**不是顺序编号**，避免对顺序的隐含依赖
3. 每个 phase 执行时，CWD 切换到自己的子目录
4. phase 间的文件传递通过 `docs/` 或通过 `## Data Flow` 表中明确定义的路径进行
5. 跨 phase 引用的文件使用相对路径（从任务根目录出发）或绝对路径
6. 合成类 phase（如 compositing）需要读取其他 phase 的输出时，通过 Data Flow 表的路径定位文件

**命名示例：**

```
- [ ] Phase 2 (browser-video-recording) — 录制视频

→ 目录 browser-video-recording-a3f8c2/
```

**两条命名线：** Checklist 的 `()` 与目录名是**不同的东西**，不要混淆：

| 位置 | 内容 | 规则 |
|------|------|------|
| Checklist `(Phase 名)` | 描述性 phase 名称 | 完整词、无 hash、无缩写，如 `(text-to-speech)` |
| 实际目录 | `<short-name>-<hash6>/` | 短名 + hash，如 `tts-a3f8c2/` |
| Data Flow 表 | 实际路径 | 目录名 + 文件名，如 `tts-a3f8c2/audio_000001.mp3` |

`()` 里的内容是给**人读的 phase 标识**，目录名是给**机器用的存储位置**。两者可以不同——`(text-to-speech)` 表示"这是 TTS 阶段"，但目录可以是 `tts-a3f8c2/`。不要照搬目录名到 `()` 中，也不要照搬 `()` 中的名称到目录名中。

好处：增删、重排步骤时，hash 不变，目录名不变，不会导致步骤对应的目录错乱。

**Execution Model:**

### Execution Model (unified runner)

When a task has a `run.py` at its root, use it as the single entry point. The auto-runner reads TASK.md checklist, marks BREAK items complete, and executes phases until the next BREAK or end of list. See [auto-runner pattern](references/auto-runner.md).

| 标注 | 行为 | 示例 |
|------|------|------|
| (无标注) | 按顺序串行，在前一阶段之后执行 | `Phase 2 — 录制视频` |
| `和 Phase X 同步进行` | 和 Phase X 并行执行 | `Phase 2 (browser-video-recording) — 和 Phase 1 同步进行, 录制视频` |
| `等待 Phase X 完成` | Phase X 完成后才执行，不关心其他阶段 | `Phase 3 (video-audio-compositing) — 等待 Phase 1 完成, 等待 Phase 2 完成, 合成` |

**Implementation:** 并行阶段通过 `delegate_task()` 启动子代理执行。等待阶段通过 `process(action='wait')` 或检查输出产物来判断完成。

**Format:**

```markdown
# Task: <Name>

## Goal

## Skills

- `text-to-speech` — 生成语音音频
- `browser-video-recording` — 录制浏览器操作视频
- `video-audio-compositing` — 合成音视频

## 环境要求

## Data Flow

| 文件 | 来源 Phase | 被消费 Phase | 格式说明 |
|------|-----------|-------------|---------|
| `{file_path}` | {phase} | {phase} | {格式文档路径} |

## Checklist

- [ ] Phase 1 (text-to-speech) — 根据解说脚本生成 N 段音频
- [ ] Phase 2 (browser-video-recording) — 和 Phase 1 同步进行, 录制浏览器操作视频
- [ ] Phase 3 (video-audio-compositing) — 等待 Phase 1 完成, 等待 Phase 2 完成, 将音频合成到视频的正确时间点
- [ ] BREAK: 检查最终视频效果
```

**Execution rule for cross-skill tasks:**

1. Read `## Skills` to know which skills to load
2. For each checklist item, identify the skill from the parenthesized prefix
3. Load that skill and follow its workflow for the phase
4. **Consult `## Data Flow`** — before writing or reading a file listed in the Data Flow table, find its `格式说明` column. That column tells you which skill's reference contains the file's schema. Load that skill and read its reference to understand the format before producing or consuming the file.
5. Pass file paths, durations, and metadata between phases via the task's `docs/` directory
6. On `task_reset`, re-run all phases in order

**执行方式（uv run）：** 如果 task 目录下有 `.venv/`（即创建了 `## Venv`），所有脚本必须通过 `uv run` 执行：

```bash
cd "$HERMES_TASKS_ROOT"/<ts>.<name>-<hash6>/
uv run python scripts/do_something.py
```

脚本内引用 skill 通用代码（`scripts/utils/`）的方式：

```python
#!/usr/bin/env python3
import sys, os
# 按需添加 skill utils 路径
sys.path.insert(0, os.path.expanduser(
    "~/.hermes/skills/<category>/<skill>/scripts"))
from utils.xxx import ...
```

**选择依据：** 有外部依赖的 skill → `uv pip install -r requirements.txt`（装进 task .venv）
纯 stdlib 的 utils/ → `sys.path` 引用，无需 pip install。

### Unified Runner (run.py)

When a task has multiple phases, add a `run.py` at the task root. Copy from `templates/run.py`.

```
./run.py                    — auto: find first unchecked item & execute until next BREAK
./run.py phase<N>           — run specific phase
./run.py list               — show checklist status
```

The auto mode:
1. Reads TASK.md checklist, finds first `[ ]` item
2. If it's a BREAK, marks it done, continues to next item
3. Executes phases until the next BREAK or end of list
4. Marks each completed phase as `[x]`

Unimplemented phases (5-7 in the template) return True (skip, don't fail).

### Current Composite Pattern: Video Recording with Audio

支持两种初始化方式：

**方式 A：从 VIDEO_PRODUCTION.md 统一规格生成**（推荐）

用一个文件描述完整流水线，`generate_all()` 自动拆解生成各子 spec。

参考 `standards/video-production-spec.md`，工具入口 `video-audio-compositing/scripts/utils/production_spec.py`：

```python
from utils.production_spec import generate_all

results = generate_all("VIDEO_PRODUCTION.md", task_dir, video_path, tts_dir)
# → RECORDING.md, SCRIPT.txt, COMPOSITING.md, SUBTITLE_SPEC.md, IMAGE_SLIDESHOW.md
```

**方式 B：手工编写各子 spec 文件**

分别编写 RECORDING.md + SCRIPT.txt + COMPOSITING.md。

---

通用执行流程（Phase 1~7）：

```
Phase 1 (text-to-speech):
  ├── 工作目录: tts/
  ├── 根据 SCRIPT.txt 逐行生成 audio_NNNNNN.mp3
  └── 输出 audio_manifest.json（增量模式：已有 manifest 时只更新改动的行）

Phase 2 (browser-video-recording):
  ├── 工作目录: recording/
  ├── 读取 RECORDING.md（用户编写的操作指令，timeline-spec 格式）
  ├── 时间驱动：在 [HH:MM:SS.mmm] 指定的时间点执行操作
  ├── 输出 video.mp4 + timestamps.json
  └── 写入 timeline.txt（含事件点和空白行）

Phase 3 (timeline-chart-preview):
  ├── 工作目录: timeline-chart-<hash6>/
  ├── 读取 COMPOSITING.md
  ├── 运行 generate_timeline_chart(format='both') — 默认生成 .txt + .png
  ├── 输出 timeline_chart.txt（文本条形图）
  └── 输出 timeline_chart.png（图片版，暗色主题）
```

**Data Flow:** 每个 phase 在自己的子目录中独立工作。跨 phase 引用使用相对路径（从 task 根目录出发）或 COMPOSITING.md 定义的路径。

**Every file cross between phases** must be documented in the task's `## Data Flow` table with a `格式说明` column pointing to the standard or skill reference that defines its schema. The executing agent reads this table to know which skill's reference to load before producing or consuming each file.

---

## TASK.md Template

**Always read the actual template at `templates/TASK.md` when creating a task.**

Every TASK.md uses:

```markdown
# Task: <Name>

## Status

active — <brief description>

## Goal

<one-liner>

## Affinity (cluster task)

`local` | `any` | `<hash6>` | `<tag>,<tag>`

## Skills (用于跨 skill 组合任务)

- `<skill-name>` — <该 skill 在本任务中的用途>

## 环境要求

| 项目 | 最低要求 | 说明 |
|------|---------|------|

## Pre-checks (optional)

*Resolve before main checklist.*
- [ ] Investigate X

## Checklist
- [ ] Phase 1 — <understanding / research>
- [ ] Phase 2 — <execution / writing / coding>
- [ ] BREAK: <optional — delete if no pause needed here>
- [ ] Phase 3 — <verification / review / cleanup>

## Tracking

<!-- 可选。每个 phase 完成后加载 `task-tracker` skill 回写状态。
     编排者读到此段后自动注入到各 phase 的 card/worker brief 中。 -->

| 参数 | 说明 |
|------|------|
| `task_dir` | 本 TASK.md 所在目录的绝对路径 |
| `phase` | 当前 phase 标识，如 `Phase 0: scrutiny-pipeline` |
| `executor` | 执行者名称 |
| `findings` | 关键发现（每行一条）|
| `outputs` | 产出文件路径（相对 task_dir）|
| `next` | 下一个 phase |

## Notes
```

### Execution Logic

**第 0 步：验证 TASK.md 格式**

**TASK.md 关键字段规范（新 task 必须遵守）：**

| 字段 | 格式 | 用途 | 解析 fallback |
|------|------|------|--------------|
| `# Task: <Name>` | 英文标题 | 任务标题（索引展示） | 任意 `# 中文标题` |
| `## Status` | 英文 | 任务状态（active/completed/—） | `## 状态` |
| `## Goal` | 英文 | 一行描述任务目标 | `## 目标` / `## 概述` |
| `## Checklist` | 英文 | `- [ ]` 步骤清单 | `## 步骤` |
| `## Notes` | 英文 | 备注信息 | `## 备注` |
| `## Related Tasks` | 英文 | 关联任务关系表（可选） | — |

`update-index.py` 优先解析英文关键字段，中文字段为向下兼容而支持。
**新 task 一律用英文关键字段。**

每次执行的第一步，检查 TASK.md 的结构：

1. `## Status` 是否存在，值是否合法（active / completed / paused / cancelled / failed）
2. `## Checklist` 是否存在
3. 每个 checklist 项是否为 `[ ]` 或 `[x]` 开头
4. BREAK 行是否放在正确的上下文位置

发现问题时**不自动修正**，先问你"TASK.md 第 X 行有问题，建议改为 YYY，可以吗？"，得到确认后再改。

**硬性规则：没有 BREAK 就不停**

两个 checklist 项之间如果没有 `[ ] BREAK:` 行，执行完前一项后**直接执行下一项**，不问"要不要继续"。`[ ] BREAK:` 是唯一合法的暂停信号。以下情况都不需要停下来问：
- Phase X 完成之后
- `和 Phase X 同步进行` 标注的依赖满足后
- 看到 "等待 Phase X 完成" 但产物已存在时

**执行逻辑：**

The agent reads TASK.md from top to bottom:

```
逐行读取:
  [x] DONE* → 跳过（用户已确认的断点）
  [x]      → 跳过（已完成）
  [ ] BREAK:* → 输出已完成摘要，退出等待
  [ ]      → 执行此项
```

**Pre-checks section** (如果存在) → 只执行 Pre-checks 下的 `[ ]` 项，输出结果，等用户确认后再进入 Checklist。

**BREAK 行** → 执行到此时暂停，输出内容给用户。用户确认后将 `[ ] BREAK:` 改成 `[x] DONE:`，下次自动跳过。


**🔴 执行纪律：非 BREAK 不停** — 完成一个 `[ ]` 项后，立即找到下一个未完成的 `[ ]` 项。如果中间没有 `[ ] BREAK:`，直接执行，绝不询问"要不要继续"。用户对停顿询问非常反感。

---

## Operations Reference

### task_list

List all active tasks, inbox proposals, and declined items:

```bash
echo "=== Active Tasks ==="
printf "%-20s %-30s %-10s %7s %5s\n" "Timestamp" "Name" "Status" "Pending" "Done"
for d in "$HERMES_TASKS_ROOT"/2*/; do
  [ -f "$d/TASK.md" ] || continue
  dir=$(basename "$d")
  ts=${dir%%.*}
  name=${dir#*.}
  status=$(grep -A2 '^## Status' "$d/TASK.md" | tail -1 | sed 's/^ *//; s/ —.*//')
  pending=$(grep -c '^- \['" "'\]' "$d/TASK.md" 2>/dev/null)
  done=$(grep -c '^- \[x\]' "$d/TASK.md" 2>/dev/null)
  printf "%-20s %-30s %-10s %3d  %3d\n" "$ts" "$name" "$status" "$pending" "$done"
done
```

For inbox and declined, see `scripts/task-list.sh` or inline:

```bash
echo "=== Inbox ==="
ls "$HERMES_TASKS_ROOT"/inbox/ 2>/dev/null || echo "  (empty)"
echo "=== Declined ==="
ls "$HERMES_TASKS_ROOT"/declined/ 2>/dev/null || echo "  (empty)"
```

### task_create <name> [description] [--skill <skill-name>] [--ticket <ticket-id>]

Create a new task with timestamped directory. **After creation, show the user the README + checklist. Do NOT fill in placeholder content based on prior conversation.**

**流程：**

0. **确定任务类型** — 根据任务目标判断属于哪种类型（`analysis`、`video-pipeline` 等），加载 `references/task-types/<类型>.md`
1. 创建 `tasks/<ts>.<name>-<hash6>/` 目录和 `input/` `output/` `scripts/`（`output/` 下按需创建 `docs/` `logs/` 子目录）
2. **如果是从 inbox 文件创建任务** — 将 inbox 源文件复制到 `input/`（该文件成为 task 自持的输入材料，不依赖 inbox 的原始路径）
3. 调用 `create_task_meta()` 生成 `.hermes-task.json`
   - 自动在 `default` 看板创建 kanban 卡片，卡片 ID 写入 `.hermes-task.json`
   - 卡片标题: `<task-name> [task:<目录名>]`
   - 卡片 assignee: `default`
4. **如果传了 `--ticket <id>`** — 将 ticket 信息写入 TASK.md 的 `## Related Tickets` 节，并将 task hash 写回 ticket 的 `task_id` 字段（实现双向关联）
5. 检查 `--skill` 指向的 skill 是否有 `scripts/create_task.py`：

   ```
   ~/.hermes/skills/<category>/<skill-name>/scripts/create_task.py
   ```

   有则委托其创建 TASK.md 和其他模板文件（skill 自己决定要生成什么）。
   没有则使用 task-framework 的默认 TASK.md 模板。

6. **Venv 管理（按需创建）：**
   遍历 `--skill` 涉及的 skills（或 TASK.md `## Skills` 中列出的），如果任意 skill 有 `scripts/` 目录（含代码），执行：

   ```bash
   cd "$HERMES_TASKS_ROOT"/<ts>.<name>-<hash6>/
   uv venv
   ```

   然后对每个有代码的 skill：

   ```bash
   # 如果 skill 有外部依赖
   [ -f ~/.hermes/skills/<category>/<skill>/scripts/requirements.txt ] && \
     uv pip install -r ~/.hermes/skills/<category>/<skill>/scripts/requirements.txt

   # 如果 skill 有 scripts/utils/（通用代码），在 task 执行脚本中通过 sys.path 引用
   # 不需要 pip install，详见执行模型章节
   ```

   如果没有任何 skill 有代码 → 跳过 venv 创建，TASK.md 中不写 `## Venv`。

7. **按需追加 `## Venv` 节到 TASK.md：**
   如果创建了 venv，在 TASK.md 末尾（Checklist 之前）追加：

   ```markdown
   ## Venv

   路径: `.venv/`
   创建: `uv venv`
   依赖:
     - <skill> (<外部包>)
   执行: `uv run python <script>`
   ```

Skill 的 `scripts/create_task.py` 接口约定：

```python
#!/usr/bin/env python3
"""create_task.py — 由 task-framework 调用。

参数: <task_dir> <task_name> <task_hash>
返回: 0 (成功) 或非0 (失败)

职责: 写入 TASK.md、REQUIREMENTS.md、或其他模版文件、创建所需目录。
"""
import sys, os
task_dir = sys.argv[1]
task_name = sys.argv[2]
task_hash = sys.argv[3]
# ... skill 自己的逻辑
```

**示例：** 创建带 browser-screen-record-task 模板的任务：

```bash
task_create "demo-video" --skill browser-screen-record-task
# → task-framework 创建目录 + .hermes-task.json
# → 创建 .venv/ + 安装依赖（playwright）
# → 委托 browser-screen-record-task/scripts/create_task.py 写 TASK.md + REQUIREMENTS.md
# → 按需追加 ## Venv 节到 TASK.md
```



**Skill-specific templates:** If this task belongs to a specific skill (e.g., `browser-video-recording`), load that skill to get its template. Use task_create for the directory structure, then apply the skill's templates on top.

**RECORDING.md dual-file pattern:** Some skills (e.g., `browser-video-recording`) use two files: a standard `TASK.md` plus a skill-specific spec file (e.g., `RECORDING.md`). When creating a task for such skills, generate BOTH files from the skill's templates directory.

### task_view <name-or-hash>

按名或 hash 定位 task 并显示 README + TASK.md：

```bash
# 1. Try hash-first: find dir containing this hash
dir=$(ls -d "$HERMES_TASKS_ROOT"/*"${1}"*/ 2>/dev/null | head -1)
# 2. Fallback: try name glob (requires full name including hash6 suffix)
if [ -z "$dir" ]; then
  dir=$(ls -d "$HERMES_TASKS_ROOT"/*."${1}"/ 2>/dev/null | head -1)
fi
if [ -z "$dir" ]; then
  echo "Task not found: $1"
  exit 1
fi
cat "$dir/README.md"
echo "---"
cat "$dir/TASK.md"
```

### task_set_status <name> <status> [reason]

Update the `## Status` line. Valid statuses:

| Status | Context | Description |
|--------|---------|-------------|
| `active` | Solo | Task is actively being worked on (non-cluster) |
| `paused` | Solo | Temporarily paused |
| `completed` | Solo | Finished (legacy, prefer `done`) |
| `cancelled` | Solo | Abandoned |
| `failed` | Solo/Cluster | Unrecoverable error; reset to `active` or `pending` to retry |
| `pending` | Cluster | Waiting to be claimed by a node |
| `claimed:<node_id>` | Cluster | Claimed by a node, not yet started |
| `in_progress` | Cluster | Being executed by the claiming node |
| `pending_review` | Cluster | Execution complete, awaiting creator confirmation |
| `done` | Cluster | Confirmed complete |

- `failed` 用于执行过程中遇到不可恢复的错误（如未找到特殊操作条目），中止执行等待修复。Cluster 中可重置为 `pending` 重新分发。

### task_inbox

List all inbox proposals. Inbox items are files or subdirectories under `tasks/inbox/`:

```markdown
tasks/inbox/
├── 20260510-生物年龄检测与逆转干预技术（深圳）.pdf   ← raw source file
├── feature-login/                                      ← directory with REQUIREMENTS.md
│   └── REQUIREMENTS.md
└── ...
```

Inbox items can be:
- **Raw files** (`.pdf`, `.docx`, `.xlsx`, `.md`, etc.) — treated as the task's input source material
- **Directories** with `REQUIREMENTS.md` — the directory may also contain additional source files

每个 inbox 子目录可以包含 `REQUIREMENTS.md`（可选），由人手工编写，描述任务的目标、输入、输出等。task-framework **不修改** REQUIREMENTS.md 的内容，只读取它作为任务创建的输入。

### task_inbox_accept <name>

将 inbox 条目转换为正式任务：

**如果 inbox 是 RAW 文件**（如 `.pdf`、`.docx`）：

1. **创建任务目录** — `tasks/<ts>.<name>-<hash6>/`
2. **移动 source 文件到 task** — `mv inbox/<file> tasks/<ts>.<name>-<hash6>/input/`（源文件成为 task 自持材料，inbox 不留残影）
3. **生成 TASK.md** — 在 Data Flow 中将 source 路径写为 `input/<filename>`
4. **通知用户** — 展示 TASK.md 内容，等待确认

**如果 inbox 是目录（无论是否存在 REQUIREMENTS.md）：**

核心原则：**改名为任务目录，整体挪入 tasks/，不 copy-leave**。避免 inbox 遗留和文件重复。

1. **读取目录内容** — 了解有哪些源文件（DESCRIPTION.md、REQUIREMENTS.md、图片、PDF 等）
2. **读取相关 skill 模板** — 根据任务类型加载对应 skill 的 templates/
3. **重命名并移动** — 将 inbox 目录原地改名为任务目录，然后整体移入 `tasks/`：

   ```bash
   # 步骤:
   # 1. 生成 timestamp + hash
   ts=$(date +%Y%m%d-%H%M%S)
   hash=$(python3 -c "import secrets; print(secrets.token_hex(3))")
   new_name="${ts}.${name}-${hash}"

   # 2. 重命名 inbox 目录（原地改名，都在 HERMES_TASKS_ROOT 内）
   mv "$HERMES_TASKS_ROOT/inbox/$old_name" "$HERMES_TASKS_ROOT/$new_name"

   # 3. 创建 task 骨架
   mkdir -p "$HERMES_TASKS_ROOT/$new_name/output/docs" "$HERMES_TASKS_ROOT/$new_name/output/logs"
   touch "$HERMES_TASKS_ROOT/$new_name/TASK.md" "$HERMES_TASKS_ROOT/$new_name/README.md"

   # 4. 将原有文件归入 input/
   #    原有的 DESCRIPTION.md / REQUIREMENTS.md / 图片 / PDF 等已在新目录下
   #    它们自动成为 input/ 材料（注入到 input/ 子目录或保持原位）
   #    如果想让结构更规整，将散落在根目录的文件移入 input/:
   for f in "$HERMES_TASKS_ROOT/$new_name"/*; do
     name=$(basename "$f")
     case "$name" in
       TASK.md|README.md|TASK_MEMORY.md|.hermes-task.json|input|output|logs|scripts|docs) ;;
       *) mv "$f" "$HERMES_TASKS_ROOT/$new_name/input/" 2>/dev/null || true ;;
     esac
   done
   ```

4. **生成 .hermes-task.json** — 写入 hash、name、创建时间
5. **生成 TASK.md** — 根据 REQUIREMENTS.md 或 DESCRIPTION.md 的描述生成初步 checklist
6. **生成 README.md** — 简单概述
7. **通知用户** — 展示目录结构和 TASK.md 内容，等待确认

**注意:** 原有 inbox 目录被 rename+move 后，inbox 中不再有任何残余。如果用户仍需要通过 inbox 引用原始描述，可在 task 的 `input/` 中找到。

如果 inbox 条目是非目录且没有 REQUIREMENTS.md 的未知格式，降级为：创建空任务，等待用户填写。

### task_inbox_decline <name> [reason]

Move to `tasks/declined/<ts>.<name>/` with DECLINED.md.

### task_run <name> <command...>

Execute a command within the task context with logging.

### task_submit <name>

Delegate to subagent via `delegate_task()` — reads TASK.md, works through checklist.

### task_reset <name> [--hard]

将任务重置到初始状态，支持从头重新执行。

**--hard** (默认): 清空所有执行产物：

1. **清空 output/** — `rm -rf output/`（删除所有生成文件，input/ 不动）
2. **重置 TASK.md** — 将所有手写的 `[x]` 改为 `[ ]`（保留 `[x] DONE:` 断点，这是用户确认过的标记）
3. **重置状态** — `task_set_status <name> active`（从 `failed`、`completed`、`cancelled`、`paused` 均可重置）
4. **更新索引** — 运行 `python3 ~/.hermes/skills/software-development/task-framework/scripts/update-index.py`

> **注意：** `rm -rf output/` 是最安全的通用清理方式。`input/` 中的源文件（PDF、REQUIREMENTS.md、images/ 等）不受影响。不需要按任务类型区分清理策略。

**使用场景：** 任务执行后需要修改操作步骤并重新从头开始执行。

```bash
# 重置任务，清空所有产物
task_reset "my-task-name"

# 重置后查看任务
task_view "my-task-name"
```

---

## Root Index Files

Two auto-generated root index files live in `tasks/`:

| File | Purpose | Content |
|------|---------|---------|
| `tasks/README.md` | Directory façade | Summary table: timestamp, name, status, description |
| `tasks/TASKS.md` | Aggregated deep view | Per-task: status, goal, full checklist with done/total counts |

Both become stale when tasks are created, updated, or change status — **always regenerate after any task operation**.

### Regeneration

Use the unified script to rebuild both files:

```bash
python3 ~/.hermes/skills/software-development/task-framework/scripts/update-index.py
```

Output:
```
Updated:
  /home/hauzer/studio/hermes/tasks/README.md  (1464B)
  /home/hauzer/studio/hermes/tasks/TASKS.md   (6912B)
  Found 9 active tasks
```

The script reads all `tasks/2*/TASK.md` files, extracts status/goal/checklist/notes, and writes both files with consistent formatting.

### 🔴 Pitfall: forgot to update indexes

A recurring issue — after creating, modifying, renaming, or deleting any task, always run the script above. This is now a mandatory post-operation step (see post-flight skill).

---

## Execution Strategies

| Strategy | When | How |
|----------|------|-----|
| **A — Inline** | Simple, <5 tool calls | Execute directly in conversation |
| **B — Script** | Well-defined steps, repeatable | Write `run.sh`, execute with `task_run` |
| **C — Subagent** | Needs reasoning, composite | `delegate_task()` with TASK.md as context |
| **D — Cron job** | Independent, outlive session | `cronjob(action='create', schedule='now')` |

Choose the lightest strategy that fits. Prefer A→B→C→D in that order.

### Script vs LLM Boundary

If an operation has a well-defined, deterministic workflow (file conversion, data transform, paper run, formatting), **write a script** — don't have the LLM re-reason through the same steps each time. The script is:

- Faster (no LLM latency)
- Deterministic (same input → same output)
- Auditable (check into git, review the logic)

If the operation needs open-ended reasoning (investigating a bug, designing a feature, evaluating results), **use Strategy C (Subagent)** — it brings the LLM's judgment to bear where it adds value.

## Scripts/ Directory Layout

### Scripts/ Directory Layout

Simple scripts go directly under `scripts/`:

```\nscripts/\n├── task-runner.sh              ← logging wrapper\n├── update-index.py             ← regenerate README.md + TASKS.md\n└── convert_md_to_pdf.py        ← doc converter\n```

For complex tools that span multiple files (a multi-step data pipeline, a paper reproduction suite), create a **subdirectory**:

```
scripts/paper-reproduce/
├── run.sh                      ← entry point
├── download-data.py            ← data preparation
├── run-experiment.py           ← experiment execution
└── compare-results.py          ← output comparison
```

The entry point (`run.sh` or `main.py`) should be the only file referenced from the operation's section in SKILL.md. The supporting files live alongside it.

## Task Lifecycle Management (`manage_task.py`)

`scripts/manage_task.py` 管理任务的完整生命周期。所有文件直接存放在任务目录下（`$HERMES_TASKS_ROOT/<ts>.<name>-<hash6>/`），单一存储，无镜像目录，无 symlink。

### 命令

```bash
# 初始化一个任务（创建目录 + TASK.md + TASK_MEMORY.md + .hermes-task.json）
python3 scripts/manage_task.py init 5d5a1a
python3 scripts/manage_task.py init tasks/20260605-233355.health-sales-demo-5d5a1a/

# 导出任务（tar.gz）
python3 scripts/manage_task.py export 5d5a1a

# 导入任务
python3 scripts/manage_task.py import tasks/20260605-233355.health-sales-demo-5d5a1a.tar.gz

# 按 hash 重建（查找最近 tar.gz）
python3 scripts/manage_task.py rebuild 5d5a1a

# 一次性迁移：将旧 ~/.hermes/personal/tasks/ 文件迁移到统一目录
python3 scripts/manage_task.py migrate

# 全量注册所有现有任务
python3 scripts/manage_task.py ensure-all

# 重建索引
python3 scripts/manage_task.py reindex

# 查看所有任务
python3 scripts/manage_task.py list
```

### tar.gz 格式

```
<ts>.<name>-<hash6>.tar.gz
└── <ts>.<name>-<hash6>/          ← 任务目录（含 input/ + output/ + TASK.md + TASK_MEMORY.md + .hermes-task.json）
```

### 跨机器迁移流程

```bash
# 源机器：导出
cd ~/studio/hermes
python3 ~/.hermes/skills/software-development/task-framework/scripts/manage_task.py export 5d5a1a
git add tasks/*5d5a1a*.tar.gz
git commit -m "export 5d5a1a"
git push

# 目标机器：拉取 + 导入
git pull
python3 ~/.hermes/skills/software-development/task-framework/scripts/manage_task.py rebuild 5d5a1a
```

### 旧任务（无 hash）的管理

无 hash 的任务（目录名不以 `-<hash6>` 结尾）需先重命名目录追加 hash 才能使用 `manage_task.py`。

### Skill 文件结构一览

```
task-framework/
├── SKILL.md                  ← 规则文档 + API 文档
├── scripts/
│   ├── task-runner.sh              ← logging wrapper
│   ├── task_ref.py                 ← ref: hash resolution + cycle detection
│   └── convert_md_to_pdf.py        ← doc converter
├── templates/
│   ├── TASK.md                     ← 任务模板
│   ├── run.py                      ← 自动化执行模板
│   └── TASK_MEMORY.md              ← per-task memory 模板
└── references/
    ├── task-hash-naming.md         ← hash 命名规则
    ├── task-format-validation.md
    ├── file-safety-lesson.md
    ├── auto-runner.md
    └── ...

---

## How to Decompose a Task

When the user says "do X" and X is complex:

1. **Ask**: "这个任务看起来包含多个操作，我拆解成以下步骤，你看看对不对？"
2. **List the operations** with brief description
3. **Sequence them** with dependencies
4. **For each operation**, note which strategy fits
5. **Write TASK.md** with operations as checklist items
6. **Present to user** for confirmation before executing

---

## Quality-Gate Integration

After modifying any TASK.md, README.md, or log file inside a task directory, run quality-gate before reporting done.

## Task Tracking (automatic phase completion log)

When TASK.md includes a `## Tracking` section, orchestrators (stratis/corvan/valros)
inject tracking instructions into each dispatched card. The executor loads
`task-tracker` skill after each phase to:
- Mark the phase checkbox `[x]` in TASK.md
- Append a structured entry to TASK_MEMORY.md
- Run `update-index.py`

See `skills/task-tracker/SKILL.md` for the parameter interface.

---

## Skill 架构规范

所有 skill 应遵循 **通用工具 + 临时脚本生成** 模式：

```
skill-name/
├── SKILL.md                  ← 规则文档 + API 文档
├── scripts/
│   ├── utils/                ← 通用工具方法（可复用，不含任务逻辑）
│   │   ├── __init__.py
│   │   ├── module_a.py
│   │   └── module_b.py
│   ├── requirements.txt      ← Python 依赖声明
│   └── setup_venv.sh         ← 创建 .venv + 安装依赖
├── .venv/                    ← 技能独立虚拟环境（gitignore）
├── templates/                ← 骨架模板
└── references/               ← 参考文档
```

**规则：**

1. **`.venv/` 在 skill 目录内** — 每个 skill 独立管理依赖，`setup_venv.sh` 一键安装
2. **通用方法放 `scripts/utils/`** — 不包含任何任务特定逻辑，纯工具函数
3. **任务特定逻辑写临时脚本** — 执行时生成 `task_script.py` 到任务目录，执行完后可清理
4. **临时脚本 import 通用方法** — `sys.path.insert(0, skill_scripts_path)` → `from utils.xxx import ...`
5. **SKILL.md 是唯一定义规则的地方** — 通用方法不包含业务规则，规则在 SKILL.md 中，由 LLM 读取后生成临时脚本

## Phase Directory Rename Procedure

When renaming phase directories (e.g. `tts/` → `tts-a3f8c2/`), the change cascades across multiple files. **Do not just rename the directory** — update all cross-references:

### Files to update

| # | File | What to check |
|---|------|---------------|
| 1 | `TASK.md` — Data Flow table | All source/consumer phase paths |
| 2 | `TASK.md` — Checklist | Phase names in parentheses `(phase-name)` — descriptive, no hash |
| 3 | `COMPOSITING.md` — Video header | `video.mp4` path |
| 4 | `COMPOSITING.md` — Timeline | Every `audio_*.mp3` / `video.mp4` path |
| 5 | `COMPOSITING.md` — Output | `## Output` section path |
| 6 | `RECORDING.md` — Output line | `output:` path |
| 7 | `scripts/composite.py` | `OUTPUT = "..."` + `timeline_chart.txt` path |
| 8 | All `.py` scripts | Hardcoded paths to renamed dirs |
| 9 | `generate_timeline_chart()` calls | Text + image output paths, if `format='both'` |

### Step-by-step

1. **Plan the mapping** — which old dir → which new dir (with hash)
2. **Rename dirs** — `mv old/ new-hash6/`
3. **Update spec files** (COMPOSITING.md, RECORDING.md) — all paths
4. **Update TASK.md** — `## Data Flow` table (use actual dir paths with hashes) + checklist `()` (descriptive phase names, no hash)
5. **Update scripts** — any hardcoded paths (composite.py is the most common offender)
6. **Verify** — grep for old path names across all task files; nothing should match except venv references and intended coincidences

### Best practice: avoid the need for rename

Generate hash suffixes at task creation time, not post-hoc. When `task_create` detects this is a multi-phase task, pre-assign hashes to all anticipated phase directories and bake them into TASK.md from the start. In the `()` use only the descriptive phase name (no hash) — the hash lives only in the directory name and Data Flow table paths.

### Timeline chart images also need update

If Phase 3 uses `generate_timeline_chart(..., format='both')`, the PNG output path is derived from the text output path (`{stem}.png`). Renaming the text path's directory automatically renames the image path too — no separate update needed, as long as both file paths share the same directory stem. If you override the output path in composite.py, update both the text and image generation paths there.

## Task Identity (`.hermes-task.json`)

每个任务在创建时生成 `.hermes-task.json`，作为任务的唯一标识和接口声明。

```json
{
  "hash": "a3f8c2",
  "name": "任务名",
  "created_at": "2026-06-05T23:00:00",
  "outputs": {},
  "dependencies": [],
  "related": [],
  "supersedes": [],

  "affinity": "any",
  "claimed_by": null,
  "requires": [],
  "required_by": [],
  "priority": 2
}
```

| 字段 | 说明 |
|------|------|
| `hash` | 6 位随机字符串，全局唯一 |
| `name` | 任务名（目录名 `ts.name` 中的 name 部分） |
| `outputs` | 命名输出，key 是输出名，value 是路径。由各 phase 填充 |
| `dependencies` | 依赖的其他任务 hash 列表（硬依赖，本任务开始前 must 完成） |
| `related` | 主题相关/互为参考的其他任务 hash 列表（无硬依赖） |
| `supersedes` | 本任务替代/废弃的旧任务 hash 列表 |
| `affinity` | Cluster 亲和性：`local` / `any` / `<hash6>` / `<capability-tag>` |
| `claimed_by` | 认领此任务的节点 hash6，未认领为 `null` |
| `requires` | 硬依赖：这些 task hash 必须 `done` 后才能认领 |
| `required_by` | 反向依赖：哪些 task 依赖本 task（下游创建时回写） |
| `priority` | 优先级：0 (最高) ~ 3 (最低)，默认 2 |

See [task-hash-naming.md](references/task-hash-naming.md) for the complete naming convention rationale.

### Named Outputs

Phase 完成后将产物路径注册为 named output：

```bash
python3 -c "
import json
with open('.hermes-task.json') as f: d = json.load(f)
d['outputs']['video'] = 'compositing-a3f8c2/output.mp4'
with open('.hermes-task.json', 'w') as f: json.dump(d, f, indent=2)
"
```

其他任务通过 `ref:hash/output_name` 引用：

```
ref:a3f8c2/video    → 解析为 compositing-a3f8c2/output.mp4
```

### 依赖声明

任务创建时或手动在 `.hermes-task.json` 中声明 `dependencies`：

```json
{
  "hash": "def456",
  "name": "下游任务",
  "dependencies": ["a3f8c2", "b7e9d1"],
  "outputs": {}
}
```

### `ref:` 解析

🔴 **IMPORTANT: resolve_ref globs `*{hash_id}*` against directory names.** The hash MUST be part of the task directory name for `ref:` resolution to work. Directory naming convention: `YYYYMMDD-HHMMSS.<name>-<hash6>/`. If the hash is only in `.hermes-task.json` and not the dir name, `ref:` lookups will return `FileNotFoundError`.

pipeline 或任意 skill 遇到 `ref:` 前缀时，调用以下逻辑：

```python
import os, glob, json

def resolve_ref(ref_str, tasks_root='~/studio/hermes/tasks'):
    if not ref_str.startswith('ref:'):
        return ref_str
    parts = ref_str[4:].split('/', 1)
    hash_id = parts[0]
    output_name = parts[1] if len(parts) > 1 else None
    tasks_root = os.path.expanduser(tasks_root)
    matches = glob.glob(os.path.join(tasks_root, f'*{hash_id}*'))
    if not matches:
        raise FileNotFoundError(f'Task with hash {hash_id} not found')
    task_dir = matches[0]
    meta_path = os.path.join(task_dir, '.hermes-task.json')
    if not os.path.exists(meta_path):
        raise FileNotFoundError(f'.hermes-task.json not found in {task_dir}')
    with open(meta_path) as f:
        meta = json.load(f)
    if output_name:
        if output_name not in meta.get('outputs', {}):
            raise KeyError(f'Output \"{output_name}\" not declared')
        return os.path.join(task_dir, meta['outputs'][output_name])
    return task_dir
```

### 循环依赖检测

创建/更新依赖时验证：

```python
def check_cycles(meta, tasks_root):
    seen = [meta['hash']]
    stack = list(meta.get('dependencies', []))
    while stack:
        h = stack.pop()
        if h in seen:
            raise ValueError(f'Cycle detected: {h} already in {seen}')
        seen.append(h)
        matches = glob.glob(os.path.join(tasks_root, f'*{h}*'))
        if matches:
            dep_meta = json.load(open(os.path.join(matches[0], '.hermes-task.json')))
            stack.extend(dep_meta.get('dependencies', []))
    return True
```

## Task Memory (TASK_MEMORY.md)

每个任务目录下有一个 `TASK_MEMORY.md`，用于在跨 session 操作同一任务时保持上下文连贯性。

### 定位

| 文件 | 用途 | 谁写 | 生命周期 |
|------|------|------|---------|
| `TASK.md` | checklist、状态、要求 | 创建时填充 | 手动维护 |
| `TASK_MEMORY.md` | 操作记录、决策、发现、阻塞原因 | 自动追加 | 按时间追加，永不删除 |
| `logs/` | 命令输出 | 自动生成 | 可清理 |
| `.hermes-task.json` | hash、outputs、依赖 | 自动维护 | 随任务更新 |

### 读写规则

**每次操作任何 task 之前：**

1. 检查该 task 目录下是否存在 `TASK_MEMORY.md`
2. 如果存在 → 读到最后 50 行，了解最近的上下文（做了什么、卡在哪、有什么发现）
3. 如果不存在 → 从 `templates/TASK_MEMORY.md` 复制模板后写入第一条记录

**每次操作之后（特别是跨 session 时）：**

在 `TASK_MEMORY.md` 末尾追加一条新记录。

### 记录格式

```
## 2026-06-06 13:00

**操作:** 重命名 task 目录 demo-video-production-v2 → health-sales-demo-5d5a1a
**原因:** 遵循新命名规则，目录名需包含 hash
**改动:**
- 目录改名
- .hermes-task.json name 字段更新
- TASK.md 执行入口路径更新
- tasks/README.md 索引重建
**状态:** 完成，等待用户确认下一步
**素材状态:** tts-a2c2bc(17段音频✅) image-slideshow-a2c2bc(封面✅) subtitle-gen-a2c2bc(字幕✅) browser-video-recording-a2c2bc(上次中断⚠️)

## 2026-06-06 14:00

**操作:** 准备运行 Phase 3 录制
**问题:** dev server 端口 5173 不可达
**解决:** tmux 重新启动 dev server
**结果:** Phase 3 录制成功（138s, 1.8MB）
**下一步:** Phase 4 合成
```

### 记录什么

- ✅ **发生了什么** — 文件名改动、pipeline 阶段、关键命令
- ✅ **为什么** — 决策理由（避免下次不知道为什么这么做）
- ✅ **问题与解决方案** — 踩过的坑和怎么解决的
- ✅ **素材状态清单** — 什么有了、什么没有、哪个坏了
- ✅ **下一步** — 这个 session 结束时停在哪
- ❌ 纯命令输出（放 logs/）
- ❌ checklist 勾选状态（放 TASK.md）
- ❌ 详细的技术规范（放 docs/）

### `task_reset` 时

`task_reset --hard` **不清除** `TASK_MEMORY.md`，只清 logs/ 和 docs/。重置后追加一条"任务已重置"记录。

### 跨 session 价值

当新 session 打开这个任务时，`TASK_MEMORY.md` 让 agent 立刻知道：
- 上次做到哪一步
- 为什么停下来
- 有什么已知问题
- 哪个素材能复用、哪个要重做

不需要翻整段对话历史来找上下文。

### 主动创建触发信号

TASK_MEMORY.md 不仅属于 `task_create` 创建的任务。当会话从简单询问演化为复杂工作时，应当**主动创建 task 目录和 TASK_MEMORY.md**。

**触发信号（任一达到即触发）：**

| 信号 | 说明 | 示例 |
|------|------|------|
| 5+ 工具调用 | 本轮已调用了 5 次以上 terminal/write_file/patch | 修 bug → 发现新问题 → 讨论方案 → 实施 → 验证 |
| 跨子系统变更 | 改动了两个以上独立子系统 | service-manager + doc server + registry |
| 设计讨论 | 出现了多方案对比、取舍、决策记录 | 方案 A/B/C 对比 → 选定一个 |
| 文件系统结构性变更 | 创建文件、迁移数据、改 schema | registry 格式迁移、新增 skill 目录 |
| 用户明确要求 | 用户说"列个清单"、"动手吧"、"继续完善" | |

**触发后的操作：**

```bash
# 1. 创建 task 目录（不打断当前工作流）
TS=$(date +%Y%m%d-%H%M%S)
HASH=$(python3 -c "import secrets; print(secrets.token_hex(3))")
DIR="$HERMES_TASKS_ROOT/${TS}.<task-name>-${HASH}"
mkdir -p "$DIR/output/docs" "$DIR/output/logs"

# 2. 写入 TASK_MEMORY.md 首条记录
cat > "$DIR/TASK_MEMORY.md" << 'EOF'
# Task Memory — <task-name>

## YYYY-MM-DD HH:MM

**操作:** <本轮已完成的操作>
**发现:** <关键发现>
**决策:** <做出的决策>
**下一步:** <下一步要做什么>
EOF

# 3. 更新索引
python3 ~/.hermes/skills/software-development/task-framework/scripts/update-index.py
```

### 追溯创建

如果 post-flight 检查发现本轮达到了触发条件但没有 task 目录，应当**事后补建**：

1. 扫描本轮所有操作记录（memory、终端输出、文件修改）
2. 按时间顺序提炼关键节点
3. 每个节点写一条 TASK_MEMORY.md 记录（操作/发现/决策/下一步）
4. 创建目录、写入、更新索引

补建时不需要写满全部细节——每个决策点提炼 2-5 行即可，重点是"为什么选了这个方案"和"踩了哪些坑"。

### 与 post-flight 联动

post-flight 的 Integrity Check 会检查"本轮的复杂程度是否达到了触发条件"，
Pending Action Scan 会处理"达到了但没有 task 目录 → 立即补建"。
TASK_MEMORY.md 的创建和维护是 post-flight 后置链的固定组成部分。

- **`.hermes-task.json` 必须在任务根目录** — 和 TASK.md 同级
- **任务被删除后引用断掉** — `resolve_ref` 会抛异常，上游任务要考虑重建
- **循环依赖在写入时检测** — 不要在运行时才发现

| Pitfall | Correction |
|---------|------------|
| Treating a composite task as a single operation | Always decompose. Complex tasks benefit from separation. |
| Skipping decomposition for "simple" coding | Even a simple feature needs: research → design → code → review. |
| Choosing wrong strategy | 5+ tool calls or reasoning → don't use A (Inline), use C (Subagent). |
| Operation catalog out of date | Add new operations as they're discovered. |
| **🔴 Never fill task placeholders from conversation history** | When user says \"create a task named X\", create an empty template with all `{placeholder}` intact. Do NOT infer URL, steps, or operations from earlier chat context unless user explicitly says \"根据上面的对话\" or similar. Corrected multiple times — the user will delete and re-create if you guess. |\n| **🔴 File moves must be ln/cp + verify + rm** | Never `mv`. Use `ln <src> <dst>`, verify with `ls -la`, then `rm <src>`. |
| **🔴 Missing `## 环境要求` in TASK.md** | Executor pre-flight forces this check. Always include it. |
| **🔴 Confirm CWD before creating tasks** | Project root must have `tasks/` dir. If not, confirm user expects `~/studio/hermes/tasks/` as base. |
| **🔴 "tasks" naming ambiguity + no manual management** | When user says "tasks" or "task", first disambiguate: (a) task-framework managed → use task_create/task_set_status/etc., never raw `mv`/`cp`/`rm` on task dirs; (b) generic concept → normal conversation. See `PROJECT_STRUCTURE.md` for the full convention. Corrected: manual `mv` on a task dir instead of using framework. |
| 🔴 Log accumulation | Clean old logs with `rm tasks/*.<name>/logs/*.YYYYMMDD-*.log`. |
| 🔴 Root index files stale | After creating/updating/deleting any task, run `python3 ~/.hermes/skills/software-development/task-framework/scripts/update-index.py` to regenerate both `tasks/README.md` and `tasks/TASKS.md`. Users rely on these indexes for overview. |
| **🔴 Data Flow table not consulted** | In cross-skill composite tasks, a phase that produces a file (e.g. TTS → `audio_manifest.json`) must write it in the format expected by the consumer phase. The `## Data Flow` table's `格式说明` column tells you where to find that format spec. Don't guess the schema — load the referenced skill/reference file and read it. Corrected in discussion about how compositing finds audio manifest format. |
| **`tasks/2*/` glob matches active tasks only** | Inbox/declined don't start with `2` — natural filtering. |
| **`## Status` empty line matters** | `grep -A2` not `-A1` to skip blank line after header. |
| LLM reasoning where a script would do | If you've repeated the same manual sequence twice, write a script. The LLM should handle judgment, not memorized mechanical steps. |
| **🔴 Don't stop & ask between checklist items unless there's a BREAK** | Execution Logic says: `[ ] BREAK:` → pause; `[ ]` → execute immediately. After completing one item, scan for the next unchecked `[ ]`. If there's no BREAK between them, execute it right away — do NOT ask 'do you want to continue?'. User corrected: '继续呀！！！你为什么要听下呢？这里有说要break吗？' Parallel dependencies (e.g. 'and Phase 1 同步进行') don't imply you should wait for instructions — check if the dependency is already resolved and act. |
| **🔴 Never modify REQUIREMENTS.md** | REQUIREMENTS.md is user-owned. If changes are needed, tell the user what to change and let them do it themselves. Do NOT edit it directly — the user won't know what changed. Corrected twice in one session. |
| **🔴 Input source files go in input/, output/ is for generated files** | `task_reset --hard` does `rm -rf output/`. Any source file (PDF, DOCX, images, REQUIREMENTS.md) placed in `output/` will be lost. Always put source material in `input/`. |
| **🔴 Inbox source files must be copied to task** | When creating a task from an inbox file (PDF/DOCX/etc.), copy the file into the task's `input/` directory. A Data Flow reference to `tasks/inbox/...` is fragile — the inbox item could be moved or deleted independently of the task. The task must be self-contained. |
| **🔴 Design discussion ≠ execution signal** | When the user makes observations, suggestions, or asks how a system/skill/process should work (e.g. "在从 REQUIREMENTS.md 生成 RECORDING.md 的时候，xxx 应该 yyy"), they are in **design/discussion mode**. Do NOT start executing pipeline steps or making code changes based on a design opinion. Wait for explicit go-ahead ("可以了" / "继续" / "跑吧"). Corrected with extreme frustration — user hadn't finished their thought. |
