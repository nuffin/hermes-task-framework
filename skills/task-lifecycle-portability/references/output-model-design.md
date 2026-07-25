# Pipeline Output Model Design (resolved 2026-06-11)

## Problem

Pipeline cleanup using exclusion-based deletion (`find ... -not -name X -exec rm`) or positive-listing always either misses cleanup targets or accidentally deletes user files. Task-framework metadata files (TASK.md, CHANGELOG.md, .hermes-task.json) mixed with pipeline artifacts in the same directory — cleanup couldn't distinguish them.

## Solution

### Directory isolation

All generated artifacts go into `output/` subdirectory; `input/` holds user source materials:

```
tasks/<ts>.<name>-<hash6>/
├── TASK.md
├── CHANGELOG.md
├── .hermes-task.json
├── input/
│   ├── REQUIREMENTS.md
│   └── images/
└── output/
    ├── tts-<hash6>/
    ├── RECORDING.md
    ├── COMPOSITING.md
    └── compositing-<hash6>/output.mp4
```

### Cleanup strategy

```bash
# pipeline.py --clean
rm -rf output/

# task_reset --hard
rm -rf output/ + reset checkboxes
```

Both entry points clean `output/` uniformly, never conflicting.

### File protection

Three core files (TASK.md, CHANGELOG.md, .hermes-task.json) live directly in the task directory. The task directory is the single source of truth — no mirror directories, no symlinks. A `rm -rf` of the entire task directory removes all task files irreversibly.

### Manage tool

`manage_task.py` commands (in task-framework skill's `scripts/`):

| Command | Action |
|---------|--------|
| `init <hash>` | Create per-hash directory + three symlinks |
| `export <hash>` | Package tar.gz (dereference symlinks) |
| `import <file>` | Restore from tar.gz |
| `rebuild <hash>` | Find hash tar.gz and import |
| `relink <hash>` | Rebuild symlinks |
| `reindex` | Rebuild tasks index |
