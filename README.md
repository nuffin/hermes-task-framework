# Task Framework for Hermes Agent

A three-layer task management system that turns complex work into structured,
trackable task directories — cross-session, cross-profile, cross-machine.

## Layers

| Layer | What | Examples |
|-------|------|----------|
| **Methodology** | How to decompose complex work | Operation catalog (`info-search`, `code-write`…), composite patterns (`software-dev`, `research`) |
| **Container** | Physical task directory structure | `tasks/<ts>.<name>-<hash6>/` with `TASK.md`, `MEMORY.md`, `CHANGELOG.md`, `input/`, `output/` |
| **Tooling** | Reusable scripts | `manage_task.py` (lifecycle), `update-index.py` (index), `task-runner.sh` (logging) |

## Skills

| Skill | Description |
|-------|-------------|
| `task-framework` | Core: methodology, container, tooling — 50+ files including scripts, templates, references |
| `task-context-storage` | Routing: global memory vs task MEMORY.md vs task CHANGELOG.md |
| `compact-directory-memory` | Storage: flat/hierarchical MEMORY.md + CHANGELOG.md formats and tooling |
| `task-tracker` | Bookkeeping: TASK.md checkbox updates, CHANGELOG.md append, index refresh |
| `task-timestamp-convention` | Naming conventions: local-time timestamps, self-explanatory names |
| `task-lifecycle-discipline` | Safe lifecycle: find-before-create, rename/delete cascades, index consistency |
| `task-aware-project-work` | Load canonical root/subsystem task context before project work |
| `task-artifact-integrity` | Validate context closure, artifacts, references, and relocation |
| `task-archaeology` | Recover missing session context from task artifacts |
| `task-cross-machine-sync` | Configurable Git synchronization of a task root |
| `task-lifecycle-edge-cases` | Recovery: TASK.md resurrection from artifacts |
| `task-lifecycle-portability` | Export/import/migration between machines via tar.gz or zip |
| `task-todo-intake` | Intake discovered requirements and route them by lifecycle scope |
| `task-nested-subtask-lifecycle` | Optional contained child-task lifecycle |
| `task-external-repos-pattern` | Cloning external git repos into task directories for analysis |

## Discovery with skill-graph

Add the repository's `skills/` directory directly to `source_dirs`:

```yaml
skills:
  config:
    skill-graph:
      source_dirs:
        - ~/path/to/hermes-task-framework/skills
```

Then use `skill_graph_search()` and `skill_load()`. No symlink, placeholder skill, or copy into `~/.hermes/skills/` is required. Package installation remains optional for environments that do not use skill-graph.

```bash
# Optional legacy/package distribution
pip install hermes-task-framework
```

## Quick Start

Create a task:

```text
Windows:  py skills/task-framework/scripts/manage_task.py create my-analysis
POSIX:    python3 skills/task-framework/scripts/manage_task.py create my-analysis
```

No Bash, `source`, `find`, `grep`, `sed`, or `awk` is required for lifecycle,
index, JSON, or archive operations. `templates/run.py` selects `.venv/Scripts/python.exe`
on Windows and `.venv/bin/python` on POSIX. Configure roots with
`HERMES_TASKS_ROOT` or `tasks.data_dir`; path containment is case-aware and
archive imports reject traversal entries. Linux/WSL tests are executable
runtime evidence. Windows and macOS have static and controlled `ntpath`
regression evidence only; no native runners were available.


List all tasks:

```bash
python3 skills/task-framework/scripts/update-index.py
cat $HERMES_TASKS_ROOT/README.md
```

## Configuration

| Env Var | Default | Purpose |
|---------|---------|---------|
| `HERMES_TASKS_ROOT` | `~/studio/hermes/tasks` | Task directory root; config `tasks.data_dir` is used when unset. The legacy `~/.hermes/tasks` compatibility directory is never populated or symlinked. |

## Repositories

| Role | Repo | PyPI |
|------|------|------|
| Skill code (this repo) | [hermes-task-framework](https://github.com/nuffin/hermes-task-framework) | — |
| Pip wrapper | [hermes-task-framework-pip](https://github.com/nuffin/hermes-task-framework-pip) | [hermes-task-framework](https://pypi.org/project/hermes-task-framework/) |

## Related

- [hermes-skill-graph](https://github.com/nuffin/hermes-skill-graph) — skill discovery plugin
