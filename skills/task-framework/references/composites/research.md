# Composite: Research Task

For open-ended investigation — competitor analysis, policy study, tech feasibility exploration.

## Sequence

```
1. info-search    → 多源搜索（竞品、论文、政策、产品）
2. data-analysis  → 整理发现、归类、对比
3. document-write → 写出调研报告
4. (optional) paper-reproduce → 如有论文需要复现
```

## Directory Structure

```
tasks/<ts>.<name>/
├── README.md                      ← 调研总结（最初空，随进度更新）
├── TASK.md                        ← 分解后的操作 checklist
├── docs/
│   ├── competitor-<company>.md    ← 每家公司一份
│   ├── paper-<short-title>.md     ← 每篇论文一份
│   ├── policy-<region>.md         ← 每个政策/报告一份
│   └── architecture-proposal.md   ← 方案建议
└── logs/
    └── ...
```

## Checklist Template

```
- [ ] Phase 1 — Define scope & targets
- [ ] Phase 2 — Collect sources (info-search)
- [ ] Phase 3 — Organize & analyze findings
- [ ] Phase 4 — Write summary report
- [ ] BREAK: 调研结果是否足够？
- [ ] Phase 5 — (optional) Architecture proposal / recommendation
```

## Pitfalls

- **Scope creep** — agree on search scope before starting, or research goes infinite
- **Source freshness** — note retrieval date on each doc; stale info = worse than no info
- **Organize as you go** — don't wait until the end to write docs/ files. Write one file per source immediately after collecting it
- **Summary table in README** — after collecting all docs, update README.md with a table linking each doc
