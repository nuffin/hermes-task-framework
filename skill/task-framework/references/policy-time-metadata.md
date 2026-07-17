# Policy / Regulatory Document Time Metadata Extraction

When processing a batch of policy or regulatory documents, extract and categorize all time-related information. This enables chronological analysis, deadline tracking, and compliance planning.

## Time Metadata Categories

### 1. Title-Embedded Period (标题自带周期)

Some policies declare their validity period in the title itself. These are the most visible:

```
浙江省加快推动"人工智能+医疗健康"高质量发展行动计划（2025—2027年）
重庆市智慧医疗装备产业创新发展行动计划（2025—2027年）
```

**Extraction pattern:** grep for parenthesized year ranges in document titles. Regex: `（\d{4}—\d{4}年）`

### 2. Target Milestone ("到 X 年" goals)

Almost every policy includes specific quantitative targets with a deadline year. These drive execution priorities.

| Pattern | Example |
|---------|---------|
| "到 2027 年，……" | 到 2027 年，适老化改造累计完成不少于 12 万户 |
| "到 2026 年……；到 2027 年……" | 分阶段目标（如 AI 普及率 70% → 80%） |

**Extraction:** grep for `到 \d{4} 年` and collect the subsequent metric + value.

### 3. Effective / Enforcement Date (施行日期)

When the policy takes legal effect:

| Source | Examples |
|--------|----------|
| "自 XXXX 年 XX 月 XX 日起施行" | 自 2025-01-22 起施行 |
| "自印发之日起施行" | 重庆市创新医疗器械管理办法 |
| "自 XXXX 年 XX 月 XX 日起执行，有效期 X 年" | 深圳宝安区措施：3 年 |

**Extraction:** grep for `自.*起施行|自.*起执行|有效期.*年`

### 4. Filing / Application Deadline (申报截止)

For competitive programs, funding applications, and pilot project solicitations:

| Source | Deadline |
|--------|----------|
| "请于 XXXX 年 XX 月 XX 日前报送" | 海珠区 AI 场景：2026-04-18 |
| "于 XXXX 年 XX 月 XX 日前将申报材料报送" | 养老机器人试点：2025-07-10 |

**Extraction:** grep for `于.*前|截止.*时间|报送.*日期`

### 5. Subsidy / Funding Expiration (补贴截止)

Each subsidy program has its own end date, often in the supporting table rather than the policy body:

| Expression | Meaning |
|------------|---------|
| "政策实施期限暂定 2026 年" | Tentative, subject to extension |
| "政策实施截至 2027 年 12 月 31 日" | Hard deadline |
| "试行 1 年" | 1-year trial from issuance date |
| "至 2028-05" | Month-level precision |
| "至 2028 年 12 月 31 日结束" | Year-end hard stop |

**Extraction:** grep for `期限|截止|结束|试行.*年|有效期` in subsidy/funding sections.

### 6. Project Execution Period (项目实施周期)

For programs that fund specific projects, the allowable execution window:

| Provision | Example |
|-----------|---------|
| "实施周期原则上不超过 X 年" | 重庆市创新医疗器械：≤ 3 年 |
| "可延长，最长 1 年" | With extension mechanism |
| "每个项目只能申请 1 次时间延长" | One-time extension limit |

### 7. Document Issuance Date (发文日期)

The official publish date from the document footer. Useful for recency assessment:

| Source | Example |
|--------|---------|
| Government document footer | 2025 年 2 月 24 日 |
| Official letter number | 粤府办〔2025〕4号（year embedded in 文号） |

## Practical Workflow

### Step 1 — Scan all documents for time patterns

Use a broad grep across all converted markdown files:

```bash
cd tasks/<task-name>/docs
grep -n -E '(有效期|截止|自.*起|至.*止|期限|到.*年|试行|实施.*年|年度)' *.md | grep -v '来源文件'
```

### Step 2 — Categorize into the 7 types above

Group results by category. Some entries may fit multiple categories — pick the primary one.

### Step 3 — Annotate the merged document

For each policy heading in the merged document, add a blockquote line:

```markdown
### Policy Name

> **发文：** 2025-02-24 ｜ **文号：** 粤府办〔2025〕4号 ｜ **目标节点：** 2027 年
> **施行：** 2025-05-18 ｜ **有效期：** 3 年（至 2028-05-18）
> **申报截止：** 2026-04-18
```

Use pipe-separated format within a single `>` line for compactness. Multiple lines only when a policy has many time attributes.

### Step 4 — Add a summary table to summary.md

In the summary document, add a comprehensive time table:

```markdown
## 政策有效期与关键时间节点

### 目标完成期限
| 政策 | 节点目标 | 期限 |
|------|---------|------|
| ... | ... | 2027年 |

### 申报截止日期
| 项目 | 截止时间 |
|------|---------|
| ... | 2026-04-18 |
```

## Pitfalls

- **文号中的年份** — 渝府办发〔2025〕57号 tells you the year is 2025, but the actual validity may extend to 2027. The 文号 year is the issuance year, not the policy period.
- **"试行" ≠ short-term** — 试行 policies often remain in effect indefinitely until formally replaced. The trial label means the policy is provisional, not that it has a hard expiration.
- **Deadlines in attachments** — critical deadlines (especially for subsidies) are often in XLSX spreadsheets or appendix tables, not the main policy body. Always scan supplementary files.
- **Cross-referencing other policies** — some policies say "有效期至 XXXX 年" but the referenced implementation rules may have a different timeline. Document both.
