# Operation: info-search

Multi-source information search and capture — competitor analysis, policy research, tech stack evaluation.

## Workflow

1. **Identify search targets** — competitors, products, papers, policies
2. **Collect from each source** — web_search, arXiv, policy databases
3. **Write findings** — one markdown file per source in `tasks/<ts>.<name>/docs/`
4. **Tag sources** — note date, source URL, confidence level
5. **Update README.md** — add summary table of collected docs

## Input

- List of search queries or targets
- Domain context (industry, technology area)

## Output

- `docs/*.md` — one file per source
- Updated `README.md` with collected-docs summary table

## Pitfalls

- Blind trust in one source — cross-validate with multiple searches
- Missing search freshness — note date of retrieval
- Scope creep — agree on search scope before starting
