# analysis 任务生命周期

## 创建

1. 创建 `tasks/<ts>.<name>-<hash6>/` 目录，含 `input/` `output/` `scripts/`
2. 从 inbox 复制源文件（PDF、DOCX、图片等）到 `input/`
3. 写入 `TASK.md`，Data Flow 中将源文件路径写为 `input/<filename>`
4. 写入 `.hermes-task.json`

## 执行

1. 从 `input/` 读取源文件
2. 生成分析文档写入 `output/docs/`
3. **如果 TASK.md 有 `## Repo` 字段：** 设计文档/分析报告放到 Repo 路径下（如 `{Repo}/docs/`），而不是 `output/docs/`
4. 执行日志仍写入 `output/logs/`（日志始终在 task 目录）
5. 最终交付物在上一步确定的路径中（Repo docs/ 或 output/docs/）

示例目录结构：

```
tasks/<ts>.<name>-<hash6>/
├── input/
│   └── source.pdf
├── output/
│   ├── docs/
│   │   ├── 01-pdf-analysis.md
│   │   ├── 02-prd-overview.md
│   │   └── 03-prd-modules.md
│   └── logs/
│       └── output.20260610-152823.log
├── TASK.md
├── README.md
├── CHANGELOG.md
└── .hermes-task.json
```

## 修改

- 修改 TASK.md checklist 正常进行
- 不需要重跑已完成的 phase，除非修改了对应的输入

## 清理

`task_reset --hard` 执行：

```bash
rm -rf output/            # 删除所有生成文档和日志
# 重置 TASK.md checkboxes
# 重置状态为 active
```

如果 task 有自定义清理需求（如保留特定目录），创建 `scripts/clean.sh` 覆盖默认行为。

`input/` 不受影响。

## 完成

1. 确认所有交付物在 `output/docs/` 中
2. 更新 TASK.md 状态为 `completed`
3. 运行 `python3 scripts/update-index.py` 更新索引
