---
author: Hermes Agent
category: software-development
description: 任务跟踪回写 — 更新 TASK.md checkbox、追加 CHANGELOG.md、刷新索引。接收通用参数，隐藏 task-framework
  内部约定
license: MIT
metadata:
  hermes:
    scenes:
    - hermes
    - writing
    tags:
    - software-development
    - task-framework
    - hermes
    - tracking
    - bookkeeping
name: task-tracker
tags:
- task
- tracking
- task-framework
- checklist
- memory
version: 1.0.0
---

# Task Tracker

## 定位

`task-tracker` 是任务层的 bookkeeping skill。它知道 task-framework 的内部约定（TASK.md checkbox 格式、CHANGELOG.md 追加格式、索引更新），对外暴露简单的参数接口。

角色不需要知道 task-framework 的任何细节——它们只需要加载 `task-tracker` 并传入参数。

## 参数

| 参数 | 必须 | 类型 | 说明 |
|------|------|------|------|
| `task_dir` | ✅ | path | TASK.md 所在目录的绝对路径 |
| `phase` | ✅ | string | 当前完成的 phase 标识，如 `Phase 0: scrutiny-pipeline` |
| `executor` | ✅ | string | 执行者名称，如 `my-agent` |
| `findings` | ❌ | list | 关键发现行 |
| `outputs` | ❌ | list | 产出文件路径（相对 task_dir） |
| `next` | ❌ | string | 后续 phase |

## 执行步骤

1. 读取 `TASK.md`
2. 找到包含 `<phase>` 文本的 `- [ ]` 行，改为 `- [x]`
3. 在 `CHANGELOG.md` 末尾追加记录：

```markdown
## <phase> — <executor>

- **执行时间**: <当前时间>
- **状态**: completed
- **关键发现**:
  - <finding line 1>
  - <finding line 2>
- **输出**:
  - `<output file 1>`
- **下一步**: <next>
```

4. 运行 `python3 scripts/update-index.py  # from the skill directory`

## 使用示例

```
加载 task-tracker：
  task_dir: $HERMES_TASKS_ROOT/<ts>.<task-name>-<hash6>
  phase: Phase 0: scrutiny-pipeline
  executor: my-agent
  findings:
    - Finding 1
    - Finding 2
  outputs:
    - output/docs/00-scrutiny-report.md
  next: Phase 1: domain-analysis
```

## 与 task-framework 的关系

`task-tracker` 封装了 task-framework 的以下操作：
- TASK.md checkbox 格式（`- [ ]` → `- [x]`）
- CHANGELOG.md 追加格式
- update-index.py 调用

task-framework 不需要知道 `task-tracker` 的存在——它只提供 task 容器。`task-tracker` 是独立工具，消费 task-framework 的产出格式。

## 与 orchestrator 的关系

Orchestrators读取 TASK.md 的 `## Tracking` 段，获取 tracker skill 名和参数定义，注入到每个 phase 的 card body 或 worker brief 中。

角色收到 card 后，在工作完成时按 brief 指令加载 `task-tracker` 并传入参数。角色不需要理解 task-framework——它只管传入参数。
