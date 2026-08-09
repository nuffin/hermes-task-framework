# external-audit 任务生命周期

## 创建

1. 创建 `tasks/<ts>.<name>-<hash6>/` 目录，含 `output/` `scripts/`（不需要 `input/`）
2. 在 TASK.md 的 Data Flow 中列出**外部源文件路径**（绝对路径，如 `~/project/docs/*.md`）
3. 写入 `TASK.md`，注明"不可修改外部文件"
4. 写入 `.hermes-task.json`

## 执行

1. 通过绝对路径读取外部源文件（`read_file`, `search_files` 工具）
2. 将分析产出写入 `output/docs/`
3. **如果 TASK.md 有 `## Repo` 字段：** 分析报告/审计文档放到 Repo 路径下（如 `{Repo}/docs/`），而不是 `output/docs/`
4. 执行日志仍写入 `output/logs/`（日志始终在 task 目录）
5. 最终交付物在上一步确定的路径中（Repo docs/ 或 output/docs/）

**🔴 核心纪律：不得以任何方式修改 input 中引用的外部路径下的文件。** 不允许 `write_file`、`patch`、`terminal(mv/cp/rm)` 等操作触及外部路径。

示例目录结构：

```
tasks/<ts>.<name>-<hash6>/
├── output/
│   ├── docs/
│   │   ├── 01-platform-audit.md
│   │   └── 02-recommendations.md
│   └── logs/
│       └── output.20260610-152823.log
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
