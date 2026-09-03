# Nested subtasks

`manage_task.py create <name> --parent <task>` creates a first-class child at
`<parent>/subtasks/<timestamp>.<name>-<hash6>/`. The parent must already exist;
children cannot create further children. The generated metadata contains
`parent_hash`, `parent_path`, `is_subtask`, and `depth`.

```bash
python3 scripts/manage_task.py create diagnostics --parent 6cff1e --desc "Bounded diagnostic work"
python3 scripts/manage_task.py list                         # roots only
python3 scripts/task_api.py describe <child-hash>             # parent + children
python3 scripts/manage_task.py view <parent-hash>             # includes child paths
python3 scripts/manage_task.py status <child-hash> done
python3 scripts/manage_task.py reset <child-hash>
python3 scripts/manage_task.py reindex                        # migrate legacy children
```

Root list and root indexes intentionally exclude nested children as independent
tasks. Parent `TASKS.md` sections list direct children. `reindex` backfills
relationship metadata for legacy directories already physically located under
`parent/subtasks/`; it does not move or delete files. `input/` is never copied
into output or removed by reset; reset only clears the selected task's output.

A child is valid only while its real path is below the exact parent's
`subtasks/` directory. Do not hand-edit metadata or move child directories.

## TODO routing

The lifecycle owner is `task-requirement-intake`; the optional nested-child
procedure is `task-nested-subtask-lifecycle`.

Requirements discovered while executing a parent belong in its `TASK.md` `## TODO` table first. At intake, post-flight, or a phase transition, classify each row as `continuous` (append/refine the parent's Checklist), `nested` (create a child with `--parent`), or `top-level` (create an independent task). Record the resulting checklist phase or task path in the outcome column and mark the row `decomposed` or `routed`. Only explicit `cancelled` or `blocked` outcomes may close a TODO; an open row is unresolved.
