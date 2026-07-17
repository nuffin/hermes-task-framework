# Pipeline Output Model Design (resolved 2026-06-11)

## Problem

Pipeline cleanup using exclusion-based deletion (`find ... -not -name X -exec rm`) or positive-listing always either misses cleanup targets or accidentally deletes user files. Task-framework metadata files (TASK.md, TASK_MEMORY.md, .hermes-task.json) mixed with pipeline artifacts in the same directory — cleanup couldn't distinguish them.

## Solution

### Directory isolation

All generated artifacts go into `output/` subdirectory; `input/` holds user source materials:

```
tasks/<ts>.<name>-<hash6>/
├── TASK.md             → symlink to ~/.hermes/personal/tasks/<hash>/task.md
├── TASK_MEMORY.md      → symlink
├── .hermes-task.json   → symlink
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

### Symlink protection

Three core files all symlinked to `~/.hermes/personal/tasks/<hash>/`. A `rm -rf` of the entire task directory only removes symlinks — actual data is preserved.

### Manage tool

`manage_task.py` commands (in task-framework skill's `scripts/`):

| Command | Action |
|---------|--------|
| `init <hash>` | Create per-hash directory + three symlinks |
| `export <hash>` | Package tar.gz (dereference symlinks) |
| `import <file>` | Restore from tar.gz |
| `rebuild <hash>` | Find hash tar.gz and import |
| `relink <hash>` | Rebuild symlinks |
| `reindex` | Rebuild ~/.hermes/personal/tasks/index.md |
