# Operation: code-write

Implement a feature or fix in code, with tests.

## Workflow

1. **Understand the requirement** — read TASK.md, PRD/TRD, existing code patterns
2. **Plan** — what files need changing, in what order (data → logic → UI)
3. **Write tests first** (TDD) — red phase
4. **Implement** — make tests pass (green)
5. **Refactor** — clean up duplication, naming, structure
6. **Verify** — run test suite, manual smoke test if applicable

## Input

- Task description or PRD section
- Existing codebase to integrate with

## Output

- Changed source files
- Passing test suite
- Updated TASK.md checklist

## Pitfalls

- Skipping test design — TDD exists because it works. Don't skip red phase.
- Over-engineering — implement the simplest thing that works first, then refactor.
- Missing edge cases — nulls, empties, boundaries, error states.
- Commit message convention — use `feat:` / `fix:` based on file functional role (skills/rules → feat, even if .md).
