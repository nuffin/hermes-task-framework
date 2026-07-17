# hermes-task-framework

[![PyPI](https://img.shields.io/pypi/v/hermes-task-framework)](https://pypi.org/project/hermes-task-framework/)

Pip-installable task management skills for [Hermes Agent](https://github.com/NousResearch/hermes-agent).

## Install

```bash
pip install hermes-task-framework
```

## What's Inside

6 skills bundled from [task-framework](https://github.com/nuffin/task-framework):

| Skill | What it does |
|-------|-------------|
| `task-framework` | Structured task lifecycle: directory, checklist, logs, scripts |
| `task-tracker` | Auto-update TASK.md checkboxes and TASK_MEMORY.md |
| `task-timestamp-convention` | Naming rules for task directories |
| `task-lifecycle-edge-cases` | Recover lost TASK.md from artifacts |
| `task-lifecycle-portability` | Export/import tasks between machines |
| `task-external-repos-pattern` | Clone external repos into task scope |

## Usage

After install, add the skills directory to your skill-graph config:

```yaml
skills:
  config:
    skill-graph:
      source_dirs:
        - ~/.hermes/skills/software-development/
```

Then in Hermes:

```
> 创建一个任务来分析这个 PDF

# The agent auto-detects task-framework, creates the directory,
# writes TASK.md + TASK_MEMORY.md, and works through the checklist.
```

## Task Structure

```
tasks/20260717-154154.task-framework-extract-standalone-fad328/
├── TASK.md              ← checklist with status + [ ] / [x]
├── TASK_MEMORY.md        ← auto-appended decision log
├── README.md             ← goal, scope, key findings
├── .hermes-task.json     ← hash, outputs, dependencies
├── input/                ← source files (never deleted)
└── output/               ← generated files (docs, logs, scripts)
```

## Development

```bash
git clone --recurse-submodules https://github.com/nuffin/hermes-task-framework.git
cd hermes-task-framework
pip install -e .
```
