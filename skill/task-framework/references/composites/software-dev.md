# Composite: Software Development

Standard round-trip for implementing a feature from scratch.

## Sequence

```
1. info-search     → 调研现有方案、技术选型、竞品参考
2. document-write  → 写四份文档（产品需求 / 产品设计 / 技术需求 / 技术设计）
3. code-write      → 实现（建议 TDD：先写测试再写代码）
4. code-review     → 自审查提交前的完整改动
5. project-tasks   → 更新 TASK.md，标记完成
```

> **Note on docs:** The user prefers a four-doc split for feature work: 产品需求 (PRD), 产品设计 (product design), 技术需求 (TRD), 技术设计 (technical design). See `references/operations/document-write.md` for details. For small/straightforward features, a PRD+TRD pair may suffice — use judgment.

## Loop Patterns

The sequence isn't always linear. Common loops:

- **PRD iteration**: 2 ↔ 用户 — 需求讨论 → 改 PRD → 再讨论
- **Dev iteration**: 3 ↔ 4 — review 发现问题 → 修复 → 重新 review
- **Architecture re-evaluation**: 3 → 1 — 实现中发现更好的方案 → 重新调研

## Checklist Template

```
- [ ] Phase 1 — Research & design (info-search + document-write)
- [ ] BREAK: 方案确认后再实现
- [ ] Phase 2 — Implementation (code-write with TDD)
- [ ] Phase 3 — Review & fix (code-review)
- [ ] BREAK: 审查结果是否接受？
- [ ] Phase 4 — Finalize & update task status
```

## Pitfalls

- **Starting coding without design** — always do info-search + document-write first. Writing code without a plan is the #1 cause of rework.
- **Forgetting BREAK points** — PRD review and code review both need a checkpoint. Add BREAK between phases.
- **Single big commit** — commit per operation, not one giant commit at the end. Each commit should be a coherent unit.
- **Skipping tests** — code-write without tests means code-review has no safety net. Always include tests.
