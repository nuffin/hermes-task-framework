# Operation: web-research

单站或多站网页调研 — 读取 URL 内容、提取关键信息、生成结构化摘要。

## 适用场景

- 竞品官网分析
- 产品/服务调研
- 技术文档速读
- 含截图附件的综合调研

## Workflow

1. **解析调研目标** — 从 TASK.md 或对话中获取 URL 列表和调研目的
2. **读取网页内容** — 对每个 URL：
   - 首选 curl（纯文本/API 端点，如 .md/.json/.yaml）
   - 次选 browser_navigate（富交互页面）
3. **处理附件** — 扫描 `input/` 目录，对截图/图片执行 OCR（tesseract）
4. **整理摘要** — 统一写入 `output/summary.md`
5. **内容讨论** — 讨论纪要写入 `output/discuss.md`

## 典型 Checklist

```
- [x] Phase 1 — 读取 <url1> 内容
- [x] Phase 2 — 读取 <url2> 内容
- [x] Phase 3 — 处理 input/ 附件（OCR）
- [x] Phase 4 — 保存 summary 到 output/summary.md
- [x] Phase 5 — 保存内容讨论到 output/discuss.md
- [ ] BREAK: 确认产出物是否符合要求
```

## Input

- URL 列表（由 TASK.md 或用户指定）
- `input/` 中的截图/图片（可选）

## Output

- `output/summary.md` — 结构化调研摘要（含来源标注）
- `output/discuss.md` — 仅限调研内容本身的后续讨论

## 工具链

| 步骤 | 工具 |
|------|------|
| 网页读取 | `curl`（纯文本）、`browser_navigate` + `browser_console`（富页面） |
| 图片 OCR | `tesseract`（`-l eng+chi_sim`）|
| 文件保存 | `write_file` 到 `output/` |

## Pitfalls

- **不保存网页原始内容** — 除非用户明确要求，summary 已提炼关键信息，避免冗余存档
- **discuss.md 只放内容讨论** — 任务元讨论（skill/pipeline 设计）是对话内容，不放任务产出物
- **OCR 可能不准** — 中文截图建议用 `chi_sim` 语言包；多语言混排用 `eng+chi_sim`
- **内容重复** — 多个页面可能有重叠信息，summary 中应去重合并
- **区分 summary 和 discuss** — summary 是调研结论（客观），discuss 是后续分析和疑问（主观）
