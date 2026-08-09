# Task Hash Naming Convention

## Why the hash must be in the directory name

`resolve_ref()` in `scripts/task_ref.py` locates tasks by globbing `*{hash_id}*` against the `tasks/` directory:

```python
matches = glob.glob(os.path.join(TASKS_ROOT, f'*{hash_id}*'))
```

This matches **directory names**, not file contents. If the hash is only in `.hermes-task.json` and not in the directory name, the glob returns nothing and `ref:` lookups fail with `FileNotFoundError`.

## The convention

```
tasks/YYYYMMDD-HHMMSS.<name>-<hash6>/
```

The hash suffix at the end of the directory name ensures:
- `resolve_ref('ref:<hash6>/...')` can find the task by matching `*<hash6>*`
- The timestamp + name part remains human-readable
- The hash is globally unique, so no collisions even with identical task names

Example:
```
tasks/<ts>.<task-name>-<hash6>/
├── .hermes-task.json     ← hash: "<hash6>", name: "<task-name>-<hash6>"
├── TASK.md
└── ...
```

## What NOT to do

- ❌ Do NOT omit the hash from the dir name — `ref:` resolution breaks
- ❌ Do NOT use sequential version suffixes (`-v1`, `-v2`) — they're not hash-based and convey no identity
- ❌ Do NOT `mv` task directories manually — use task-framework tools. Manual rename breaks the `ref:` system across all referring tasks until the directory name is updated to match

## Consistency with phase directories

Phase output directories use the same `<short-name>-<hash6>/` pattern (e.g. `tts-a3f8c2/`, `compositing-c9f3a2/`). The task directory is just the top-level version of the same convention: `<ts>.<name>-<hash6>/`.
