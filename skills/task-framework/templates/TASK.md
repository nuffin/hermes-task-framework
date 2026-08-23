# Task: <Name>

<!--
  TASK.md 关键字段规范（所有 task 遵守）：
  - # Task: <Name>         — 标题（英文）
  - ## Status              — 状态（英文）
  - ## Goal                — 目标（英文）
  - ## Checklist           — 步骤清单（英文）
  - ## Notes               — 备注（英文）
  - ## Related Tasks       — 关联任务关系表（可选）
  脚本 update-index.py 只解析以上英文关键字段。
  中文字段（## 状态、## 目标、## 步骤）为向下兼容而支持，新 task 请用英文。
-->

## Status

active — <brief description of current work>

## Goal

<one-liner>

## Skills (用于跨 skill 组合任务)

- `<skill-name>` — <该 skill 在本任务中的用途>

## Repo

<!-- 可选字段。若任务关联独立的项目仓库，在此声明路径。
     所有源码级产出（设计文档、代码、配置、测试）放到此仓库中，
     而非 task/output/。执行日志和调试信息仍放在 task/output/logs/。
     没有此字段时，所有产出放 task/output/（默认行为）。 -->

路径: `<absolute path to project repo>`
用途: <一句话描述>

## Affinity (cluster task)

<!-- 控制此任务被哪个节点认领。影响 .hermes-task.json 的 affinity 字段。
     不带 cluster 时此字段无任何效果，保留无害。 -->

- `any` — 任何节点可认领
- `<hash6>` — 指定节点（推荐；跨机器同步安全）
- `<suite-name>` — 拥有此套件的节点（如 `<suite-name>`）
- `<tag>` — 能力标签匹配（如 `gpu`, `docker`）
- 逗号分隔 → AND 逻辑（`<suite-name>,gpu` 两样都有才匹配）

注意：不要用 `local`。tasks repo 同步到其他机器后，每台都会把 `local` 当成自己的任务，造成混乱。用 node_id（hash6）代替。

## 环境要求

| 项目 | 最低要求 | 说明 |
|------|---------|------|
| Python | <版本> | <说明> |
| <依赖项> | <版本> | <说明> |
| 磁盘 | <空闲空间> | <用途> |
| API Key | <Key 名称> | <用途说明> |

## Data Flow

跨 phase 文件传递路径。phase 执行时 CWD 在自己的子目录，跨目录引用使用相对路径（`../`）。

| 文件 | 来源 Phase | 被消费 Phase | 格式说明 |
|------|-----------|-------------|---------|
| `phase_01_<skill>/<file>` | Phase 1 | Phase N | <格式文档> |
| `phase_02_<skill>/<file>` | Phase 2 | Phase N | <格式文档> |

## Phase 目录

- `phase_01_<skill>/` — <产出物说明>
- `phase_02_<skill>/` — <产出物说明>
- `phase_03_<skill>/` — <产出物说明>

## Checklist

<!-- The optional BREAK below is a template placeholder, not a real pause.
     During concrete planning, delete it or replace it with a specific pause.
     It must not block the first concrete dependency-ready checklist item. -->
- [ ] Phase 1 — <investigation / reading / understanding>
- [ ] Phase 2 — <execution / writing / implementation>
- [ ] BREAK: <optional — delete if no pause needed here>
- [ ] Phase 3 — <verification / review / cleanup>

## Tracking

<!-- 可选。每个 phase 完成后需要更新的跟踪记录。
     编排者（orchestrators）读到本节后，自动注入到各 phase 的 card/worker brief 中。 -->

加载 `task-tracker` skill，传入以下参数：

| 参数 | 值 | 说明 |
|------|-----|------|
| `task_dir` | 本 TASK.md 所在目录的绝对路径 | 让 tracker 定位任务 |
| `phase` | 当前完成的 phase 标识 | 如 Phase 0: scrutiny-pipeline |
| `executor` | 执行者名称 | 如 my-agent |
| `findings` | 关键发现（每行一条） | 从产出中提炼 3-5 条 |
| `outputs` | 产出文件路径（相对 task_dir） | 如 output/docs/00-report.md |
| `next` | 下一个 phase | 如 Phase 1: domain-analysis |

## Notes

## Related Tickets

<!-- 可选。关联的 ticket。填写 ticket_id 后 task_create 会自动将 task hash 写回 ticket 的 task_id 字段。 -->

| Ticket ID | 关系说明 |
|-----------|---------|
| `#<ticket_id>` | 创建源 / 相关事项 |

## Related Tasks

<!-- 可选。关联任务关系表：depends_on = 前置依赖（本任务开始前必须完成），related = 主题相关/互为参考，supersedes = 本任务替代/废弃了哪个旧任务 -->
| 类型 | 关联 Task | 关系说明 |
|------|----------|---------|
| depends_on | `YYYYMMDD-HHMMSS.<name>-<hash6>/` | 本任务依赖的前置任务 |
| related | `YYYYMMDD-HHMMSS.<name>-<hash6>/` | 主题相关、互为参考 |
| supersedes | `YYYYMMDD-HHMMSS.<name>-<hash6>/` | 本任务替代/废弃了哪个旧任务 |
