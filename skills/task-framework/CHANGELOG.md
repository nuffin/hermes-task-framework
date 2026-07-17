# Changelog — task-framework

## 2026-06-06

- feat: hash-based task_view — search by hash, name glob fallback (92b838d)
- feat: scripts layout — task-runner.sh, task_ref.py with ref: resolution + cycle detection (92b838d)
- feat: TASK_MEMORY.md template — per-task memory with append-only log format (92b838d, 435f85d)
- fix: browser-screen-record-task scripts/ path alignment (927124f)
- feat: venv management — auto uv venv + pip install per task (927124f)

## 2026-06-05

- feat: timeline chart preview — Phase 3 generate_timeline_chart() shows text bar chart before compositing (c1c0b24)
- refactor: phase dir naming — name-hash6/ instead of phase_NN_name-hash6/ (f3adf22)
- refactor: hash naming — random 6-char hash instead of sequential naming (f4adfb5)
- feat: inbox REQUIREMENTS.md — human-only input file, task-framework never modifies (723c68b)
- refactor: skill architecture — generic utils/ in scripts/, skill-local .venv, script generation pattern (26e1383)
- feat: TASK.md validation — pre-execution format check, no auto-fix, ask first (2d24006)
- feat: personal/standards symlink support (3ed3c85)
- feat: phase isolation directories for cross-skill composite tasks (05ab115)
- docs: timestamp conversion — separate .mmm and .mmmmmm sections (14b7a68)
- feat: Data Flow table — links files to format docs in composite task templates (7de9fcb)
- feat: composite task model — parallel execution (和 Phase X 同步进行), dependency waits (等待 Phase X 完成) (17a7d26)
- feat: cross-skill composite task support — Skills section, dependency resolution (658c4bc)
- fix: no-placeholder-guessing rule — never fill task placeholders from conversation (78b0388)
- fix: English-only commit messages in quality-gate (78b0388)
- feat: failed status — task_setstatus supports failed/completed/cancelled/paused
- feat: task_reset — reset checkboxes, clear logs/docs, re-enable re-execution
- refactor: four-doc split — PRD + product design + TRD + tech design document-write ref

## 2026-06-04

- fix: document-write references — update to four-doc split
- fix: PROJECT_STRUCTURE.md — tasks path ~/tasks/ → ~/studio/hermes/tasks/

## 2026-06-03

- feat: initial task-framework skill
- Three-layer model: Methodology / Container / Tooling
- Operation catalog: info-search, code-write, paper-reproduce, document-write, code-review, data-analysis
- Composite patterns: software-dev, research, code-review-session
- Task directory structure: tasks/<ts>.<name>-<hash6>/ with TASK.md, README.md, logs/, docs/, scripts/
- Task lifecycle: task_create, task_view, task_list, task_setstatus, task_inbox, task_inbox_accept, task_inbox_decline, task_run, task_submit, task_reset
- Execution strategies: Inline / Script / Subagent / Cron
- Merge from project-tasks skill
