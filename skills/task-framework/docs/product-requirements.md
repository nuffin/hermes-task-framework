# Task Framework — 产品需求文档

> **版本:** v1.0
> **状态:** 已投入使用
> **最后修改:** 2026-06-03 21:50

## 一、概述

Task Framework 是 Hermes Personal Suite 的核心技能之一，提供从任务创建、执行到归档的完整工作流。它覆盖三层能力：

- **方法论** — 如何把一句话需求拆成可执行的操作
- **容器** — 如何在文件系统中有序组织任务产物
- **工具** — 如何复用执行脚本和模板

## 二、能力范围

### 2.1 任务生命周期管理

| 阶段 | 能力 | 入口 |
|------|------|------|
| 提议 | 收件箱接收任务 idea | `tasks/inbox/` |
| 创建 | 自动生成时间戳目录、README、TASK.md | `task_create` |
| 执行 | 支持 4 种执行策略 | Inline / Script / Subagent / Cron |
| 跟踪 | CHECKLIST 逐项推进，BREAK 暂停点 | TASK.md |
| 暂停/恢复 | 跨会话持续跟踪 | Status 标记 |
| 完成/取消 | 归档或删除 | `task_setstatus` |

### 2.2 操作分解

将复杂任务拆解为标准操作：

- `info-search` — 多源信息搜索
- `code-write` — 代码实现
- `paper-reproduce` — 论文复现
- `file-concat` / `file-convert` — 文件加工
- `document-write` — 文档编写
- `code-review` — 代码审查
- `data-analysis` — 数据分析
- `infra-setup` — 基础设施

### 2.3 组合模式

预定义的常见工作流序列：

- `software-dev` — 调研→设计→编码→审查
- `research` — 搜索→分析→报告
- `code-review-session` — 审查→记录→更新

## 三、用户故事

| ID | 用户故事 |
|----|----------|
| US-01 | 作为用户，我希望一句话告诉助手我要做什么，助手自动拆成可执行的 checklist |
| US-02 | 作为用户，我希望任务在执行中途可以暂停，我确认后再继续 |
| US-03 | 作为用户，我希望每次执行的输出自动保存，方便追溯 |
| US-04 | 作为用户，我希望临时想到的任务可以先放到收件箱，稍后再决定是否做 |
| US-05 | 作为用户，我希望不同类型的任务（调研、编码、文档）有不同的 checklist 模板 |

## 四、与 Hermes 生态的关系

| 组件 | 关系 |
|------|------|
| `quality-gate` skill | 任务修改后自动触发质量门禁 |
| `GIT.md` rule | git 操作前置同步（Pre-Change Sync）和后置清理（Post-Change Workflow） |
| `dump-to-stage` skill | 任务的记忆备份不冲突 — task-framework 管任务内容，dump-to-stage 管系统状态 |
