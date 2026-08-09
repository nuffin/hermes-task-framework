# Parallel Research Workflow

Use delegate_task with parallel subagents for comprehensive research tasks. Each subagent covers one well-scoped direction and produces structured markdown files.

## When to Use

- Market research / competitive analysis
- Policy and regulatory research
- Technology landscape scanning
- Multi-angle topic investigations
- Any research that can be naturally split into independent streams

## Phased Research Lifecycle

Complex research projects benefit from a phased approach where each phase produces output that feeds the next:

| Phase | Focus | Delegation pattern | Output |
|-------|-------|-------------------|--------|
| 1 — Broad scoping | Initial search, landscape overview | Inline (manual search) | README.md + 2-3 docs/ files |
| 2 — Deep dive | Competitor/product deep research | 1 subagent (multiple competitors serial) | 5-6 competitor-*.md files |
| 3 — Comprehensive | Policy + patents + keywords + ecosystem | 3 parallel subagents | 5+ docs covering all dimensions |
| 4 — Technical feasibility | Deep technical analysis | 1 deep subagent | 1 large comprehensive doc |
| 5 — Synthesis | Cross-document compilation | 1 synthesis subagent reading all prior docs | Final product plan doc |

### Phase transition flow

After each phase completes:

1. Read the subagent summary (not just the file — check the summary section)
2. Verify files were written: `ls -lh docs/`
3. Mark the phase `[x]` in TASK.md
4. Update README.md with a summary table of new docs
5. Present cross-document insights to the user
6. If the user provides additional guidance (new keywords, new angles), capture it in TASK.md's Notes section, then adjust the next phase's scope
7. Ask "continue to next phase?" before proceeding

## Delegation Patterns by Phase Type

### Broad scoping (Phase 1)
**Strategy:** Inline. Do the searches yourself, compile into docs manually.

### Multi-competitor deep dive (Phase 2)
**Strategy:** One subagent, many targets. Give it a list of 5-8 competitors and let it work through them serially within one delegate_task call. Each competitor gets its own file.

```python
delegate_task(
    goal="Research 6 competitors in this market",
    context="""...
    # Save each as docs/competitor-<name>.md
    # Each file must end with a 启示 (Implications) section
    """,
    toolsets=["terminal", "file", "browser"]
)
```

### Multi-dimensional research (Phase 3)
**Strategy:** Parallel subagents, each covering a different dimension. Split by natural fault lines (policy / technology / products / ecosystem), not by source.

```python
delegate_task(
    tasks=[
        {"goal": "Research policy & industry reports", ...},
        {"goal": "Research patents & expanded keywords", ...},
        {"goal": "Research companion products & startups", ...},
    ]
)
```

Each subagent produces 1-2 docs. The content should be non-overlapping.

### Deep technical analysis (Phase 4)
**Strategy:** One deep subagent with a comprehensive spec. Give it 7-8 required sections as a template, lots of context from prior phases.

### Synthesis / product planning (Phase 5)
**Strategy:** One synthesis subagent with instructions to READ all prior docs, then produce the final document. Grant `file` toolset so it can read existing material.

```python
delegate_task(
    goal="Synthesize all research into product plan",
    context=f"""Read all docs from docs/ directory, then produce product-plan-draft.md
    with 8 chapters...""",
    toolsets=["terminal", "file"]
)
```

## Split the research domain

Identify natural fault lines and split into parallel tasks:

| Good split | Bad split |
|-----------|-----------|
| Competitor A / Competitor B / Competitor C | Feature 1 of A / Feature 2 of A / History of A |
| Policy / Patents / Products | Same source queried 3 ways |
| Domestic / International / Technology | Overlapping company lists |

Each task must be **independent** — no shared intermediate state.

## Write task specs with explicit output directives

Each subagent's prompt must include:

```
1. Research scope (what to search)
2. Output file path (absolute, where to save)
3. File format (sections, required headers)
4. Naming convention (prefix conventions like `competitor-`, `paper-`, `policy-`)
```

Example task spec:

```
"context": "输出文件：$HERMES_TASKS_ROOT/<ts>.<name>/docs/competitor-<name>.md
格式规范：
# 亲家科技
## 产品体系
(功能模块列表)
## 目标客户
## 技术栈
## 案例
## 启示（对本项目的参考价值）"
```

## Run parallel subagents

```python
delegate_task(
    tasks=[
        {"goal": "...", "context": "...", "toolsets": ["terminal", "file", "browser"]},
        {"goal": "...", "context": "...", "toolsets": ["terminal", "file", "browser"]},
        {"goal": "...", "context": "...", "toolsets": ["terminal", "file", "browser"]},
    ]
)
```

Max concurrent tasks: 3 (adjust per environment). Time budget: ~5-10 min each.

## Compile results

After all subagents return:

1. Read the summary sections of each result
2. Verify files were actually written (`ls -lh docs/`)
3. Update `TASK.md`: mark the phase as `[x]`
4. Update `README.md`: add a summary table of collected docs
5. Present cross-document insights to the user

## Output File Naming Convention

| Prefix | Use case |
|--------|----------|
| `competitor-<company>.md` | One company/competitor per file |
| `paper-<short-title>.md` | Academic paper review |
| `policy-<topic>-<year>.md` | Policy/regulatory research |
| `patent-<direction>.md` | Patent landscape |
| `extended-keywords-<topic>.md` | Keyword-expanded product discovery |
| `companion-products.md` | Companion/care products |
| `startup-bp-landscape.md` | Startup business model analysis |
| `industry-report-<topic>.md` | Market data and forecasts |
| `architecture-proposal.md` | Technical architecture design |
| `tech-feasibility-analysis.md` | Technology stack evaluation |
| `product-plan-draft.md` | Final product plan |

Each file should include a "启示" (Implications) section at the end showing relevance to the project.

## Research Methodology Tips

### Keyword expansion

Start with a core term and snowball outward. Example:

```
康养
  ├── 银发经济
  ├── 智慧助老
  ├── 居家适老化改造
  ├── 慢病管理
  ├── 医养结合
  ├── 社区养老
  ├── 老年人陪护
  └── AI陪聊
```

Each expanded keyword surfaces a different set of products, companies, and policy frameworks. Review the user's guidance mid-project — they may suggest additional keywords that were not in the original scope. Capture these in TASK.md's Notes section and incorporate into the next phase.

### Multi-source strategy

| Source | Type | What to look for |
|--------|------|-----------------|
| arXiv | Academic | Foundation research, emerging techniques |
| 中国专利数据库 | Patent | Productized technology, applicant landscape |
| 36氪/IT桔子 | Startup | Funding rounds, business models, pitch decks |
| 政府网站 (gov.cn) | Policy | Directives, pilot programs, subsidy criteria |
| Company websites | Product | Feature lists, pricing, case studies, team |
| 工信部目录 | Directory | Approved products, vendor lists |

### Output quality tracking

After each phase, log the cumulative document count and line count so the user can see progress:

```bash
find docs/ -name '*.md' -exec wc -l {} + | sort -rn
du -sh .
```

### User guidance integration mid-project

When the user provides additional research directions mid-project (common in exploratory research):

1. Add the new directions to TASK.md as a bullet list under "## Notes" or a dedicated "## 新增调研方向" section
2. Update the next phase's scope to incorporate them
3. Don't restart — fold into the next delegation call

### Pitfalls

- **Chinese search engines block bots** — Bing.cn with `&cc=cn` works sometimes, but expect 50% failure. Use gov.cn and 36氪 as fallback sources.
- **Company websites return 403** — some older Chinese sites block non-China IPs. Use cached pages or third-party descriptions.
- **Pricing is rarely public** — Chinese B-end SaaS products rarely list prices. Infer from case study size and funding data.
- **Subagent summaries can be wrong** — always verify file writes with `ls -lh` after delegation returns.
- **Subagent output limits** — very large research docs (>800 lines) may approach context limits. Split into 2 documents if a single subagent produces huge output.
- **Parallel task independence** — subagents cannot read each other's output mid-run. Each must be fully self-contained with all context provided in the prompt.
