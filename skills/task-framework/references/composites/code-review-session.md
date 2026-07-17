# Composite: Code Review Session

For a batch review of changes — diff analysis, quality gate, security scan, and report generation.

## Sequence

```
1. 加载 TASK.md / 确认审查范围
2. code-review      → 逐个文件审阅（diff, security, quality gate）
3. document-write   → 写 review/SUMMARY.md（S-XXX 建议表）
4. 更新 TASK.md 状态
5. (optional) quality-gate → 跑完整质量门禁
```

## Checklist Template

```
- [ ] Phase 1 — Understand what changed (git diff, scope)
- [ ] Phase 2 — Review each file (logic, security, style)
- [ ] Phase 3 — Run quality gate
- [ ] Phase 4 — Write review/SUMMARY.md with S-XXX items
- [ ] BREAK: 审查结果是否接受？
- [ ] Phase 5 — Fix critical issues / mark non-blockers
```

## Pitfalls

- **Scope confusion** — confirm which changes are being reviewed before starting. A session with mixed concerns produces unusable review output
- **S-XXX numbering** — each issue gets a unique S-XXX ID. New session → continue from last S-XXX, don't restart at S-001
- **Don't skip quality gate** — review without quality gate misses automated issues (lint, type errors, test failures)
