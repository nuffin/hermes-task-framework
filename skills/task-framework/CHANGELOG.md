# Changelog — task-framework

## 2026-08-06 (v1.1.0)

### feat: manage_task.py — 6 new lifecycle commands
- `create` — directory + hash + meta + templates + optional inbox move
- `accept` — create task from inbox file/dir (auto-derives name)
- `decline` — move inbox item to declined/ with DECLINED.md
- `status` — update ## Status line + auto index update
- `view` — print README.md + TASK.md (hash/dir/name resolution)
- `reset` — clear output/ + reset checkboxes + set status active (--no-hard for soft reset)
- All commands use cp+verify+rm for file moves (never raw mv)
- All commands auto-run update-index.py after changes

### fix: code quality (A1-A4, B1/B4/B6, C2/C3/C6)
- A1: replace 4 stale ~/.hermes/skills/ hardcoded paths with relative scripts/ paths
- A2: cmd_init .hermes-task.json schema 5→12 fields (matches cmd_create)
- A3: unify three index systems — reindex calls update-index.py, list scans dirs directly
- A4: task-runner.sh log path logs/ → output/logs/ (matches task_reset cleanup scope)
- B1: hash6() uses secrets.token_hex(3) instead of md5(random) across all 3 scripts
- B4: _safe_move_file/_safe_move_dir rollback on failure (clean dst, preserve src)
- B6: cmd_decline uses os.path.basename() to prevent path injection
- C2: remove stale "Skill 文件结构一览" section (listed 3 scripts, actually 5)
- C3: add .gitignore, remove tracked __pycache__/*.pyc
- C6: unify env var resolution — all 3 scripts share _resolve_tasks_root() (HERMES_TASKS_ROOT | HERMES_TASKS_DIR → profile config → global config → fallback)

### docs: SKILL.md updates (D1-D5)
- D1: trigger signal section uses manage_task.py create instead of ad-hoc bash
- D3: update create_task.py reference to manage_task.py create
- D4: Named Outputs uses task_ref.set_output() instead of inline python -c
- D5: resolve_ref/check_cycles reference scripts/task_ref.py instead of inline code

## 2026-06-06

- feat: hash-based task_view — search by hash, name glob fallback (92b838d)
- feat: scripts layout — task-runner.sh, task_ref.py with ref: resolution + cycle detection (92b838d)
- feat: CHANGELOG.md template — per-task memory with append-only log format (92b838d, 435f85d)
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
