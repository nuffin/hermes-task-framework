# external-audit 任务生命周期

## 创建

1. 创建 `tasks/<ts>.<name>-<hash6>/` 目录，含 `input/` `output/` `cache/` `scripts/`
2. 在 `TASK.md` 的 `## Authorized External Targets` 表中列出每个**外部源文件路径**（精确绝对路径，如 `/home/example/project/docs/overview.md`）、允许的只读操作和授权来源；不得使用 `~`、glob或目录通配符代替一个明确目标
3. 写入 `TASK.md`，注明外部目标默认不可修改；不得由仓库名称或关联关系推断额外范围
4. 写入 `.hermes-task.json`

## 执行

1. 只读取当前用户明确指名的外部目标，或 `## Authorized External Targets` 中逐项列出的精确绝对路径（`read_file`, `search_files` 工具）
2. 将分析产出写入 `output/docs/`
3. 执行日志仍写入 `output/logs/`（日志始终在 task 目录）
4. 最终交付物在 `output/docs/`，除非用户或任务要求明确登记了另一个外部交付目标

**🔴 核心纪律：外部路径必须逐项显式授权。** 未被当前用户明确指名、也未在任务表中登记的路径一律不得读取或操作；已授权的审计源默认只读，不允许 `write_file`、`patch`、`terminal(mv/cp/rm)` 等修改操作触及外部路径。

示例目录结构：

```
tasks/<ts>.<name>-<hash6>/
├── output/
│   ├── docs/
│   │   ├── 01-platform-audit.md
│   │   └── 02-recommendations.md
│   └── logs/
│       └── output.20260610-152823.log
├── cache/
│   └── reproducible-work-state/
├── TASK.md
├── README.md
└── .hermes-task.json
```

## 修改

- 修改 TASK.md checklist 正常进行
- 如果需要重新分析，重新读取外部文件即可

## 清理

`task_reset --hard` 执行：

```bash
rm -rf output/            # 删除所有分析文档和日志
# 重置 TASK.md checkboxes
# 重置状态为 active
```

外部文件不受影响（本来就不在任务目录内）。

## 完成

1. 确认所有交付物在 `output/docs/` 中
2. 更新 TASK.md 状态为 `completed`
3. 运行 `python3 scripts/update-index.py` 更新索引
