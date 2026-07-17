# Task Framework for Hermes Agent

A three-layer task management system that turns complex work into structured,
trackable task directories — cross-session, cross-profile, cross-machine.

## Layers

| Layer | What | Examples |
|-------|------|----------|
| **Methodology** | How to decompose complex work | Operation catalog (`info-search`, `code-write`…), composite patterns (`software-dev`, `research`) |
| **Container** | Physical task directory structure | `tasks/<ts>.<name>-<hash6>/` with `TASK.md`, `TASK_MEMORY.md`, `input/`, `output/` |
| **Tooling** | Reusable scripts | `manage_task.py` (lifecycle), `update-index.py` (index), `task-runner.sh` (logging) |

## Skills

| Skill | Description |
|-------|-------------|
| `task-framework` | Core: methodology, container, tooling — 50+ files including scripts, templates, references |
| `task-tracker` | Bookkeeping: TASK.md checkbox updates, TASK_MEMORY.md append, index refresh |
| `task-timestamp-convention` | Naming conventions: local-time timestamps, self-explanatory names |
| `task-lifecycle-edge-cases` | Recovery: TASK.md resurrection from artifacts |
| `task-lifecycle-portability` | Export/import/migration between machines via tar.gz |
| `task-external-repos-pattern` | Cloning external git repos into task directories for analysis |

## Install

```bash
git clone https://github.com/nuffin/task-framework.git
cd task-framework
./install.sh              # copy to ~/.hermes/skills/software-development/
./install.sh --symlink    # symlink for development
```

Or via pip:

```bash
pip install hermes-task-framework
```

Add to skill-graph source_dirs in `config.yaml`:

```yaml
skills:
  config:
    skill-graph:
      source_dirs:
        - ~/.hermes/skills/software-development/
```

## Quick Start

Create a task:

```bash
source ~/.hermes/personal/env.sh
TS=$(date +%Y%m%d-%H%M%S)
HASH=$(python3 -c "import secrets; print(secrets.token_hex(3))")
DIR="$HERMES_TASKS_ROOT/${TS}.my-analysis-${HASH}"
mkdir -p "$DIR/output/docs" "$DIR/output/logs"
```

List all tasks:

```bash
python3 skills/task-framework/scripts/update-index.py
cat $HERMES_TASKS_ROOT/README.md
```

## Configuration

| Env Var | Default | Purpose |
|---------|---------|---------|
| `HERMES_TASKS_ROOT` | `~/studio/hermes/tasks` | Task directory root |

## Related

- [hermes-task-framework](https://github.com/nuffin/hermes-task-framework) — pip wrapper
- [hermes-skill-graph](https://github.com/nuffin/hermes-skill-graph) — skill discovery plugin
