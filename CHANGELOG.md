# Changelog

## v1.0.1 (2026-07-18)

> task-framework `da9609f` → `dc6d900`

### extra_references_dir 支持

`task_create --skill <name>` 时，如果 skill 的 SKILL.md frontmatter 声明了 `extra_references_dir`，自动将该目录下所有文件复制到新任务目录。不覆盖已存在的同名文件。

使用方式：skill 在 `references/task-template/` 放置模板文件（搭配清单、pick 脚本、TASK 骨架），创建任务时自动部署。

### README 补全

完整 README 覆盖安装、目录结构、配置文件、skill 图集成。

## v1.0.0 (2026-06-05)

- 三层任务系统：methodology + container + tooling
- 任务目录结构（TASK.md / TASK_MEMORY.md / input/ / output/）
- 组合任务模式（software-dev / research / code-review）
- 跨 skill 组合任务 + phase 隔离目录
- 自动化执行器（run.py）
- `.hermes-task.json` 身份文件（named outputs + 依赖追踪）
- `manage_task.py` 生命周期管理
- 收件箱工作流（accept/decline）
- 根索引文件自动重建
