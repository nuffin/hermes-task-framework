# Health Sales Demo (5d5a1a) Recovery

Task: `20260605-233355.health-sales-demo-5d5a1a` — 主动健康销售管理系统演示视频

## How TASK.md was lost (historical)

1. Original TASK.md existed on June 7 with full 76-line checklist
2. During pipeline bug fixing, exclusion-based cleanup was used (instead of `rm -rf output/`)
3. TASK.md was accidentally caught in the cleanup
4. Discovered missing on June 10 — agent noted it was gone but did NOT regenerate
5. Remained missing until June 11 when user explicitly asked for it

## Recovery process (June 11)

1. Searched filesystem — no TASK.md found in task directory
2. Read REQUIREMENTS.md → extracted timeline, language, viewport
3. Read TASK_MEMORY.md (was already a symlink, content preserved) → knew last state (completed)
4. Listed directory contents → found all phase dirs (tts-6d3e4c, compositing-6d3e4c, etc.)
5. Read `.hermes-task.json` → outputs mapping confirmed all phases done
6. Loaded `browser-screen-record-task` skill → got canonical phase decomposition
7. Compared first draft against skill's template:
   - Missing Phase 2 (timeline-composer)
   - Wrong phase order (TTS→record→cover→subtitle instead of parallel)
   - Extra phases (subtitle-compositing, timeline-chart-preview are subsumed by composite)
8. Fixed TASK.md to match skill's phase structure, all items marked [x]

## Subsequent migration to symlink + output/ model

After recovery, the task was migrated to the new structure:

```
tasks/<ts>.<name>-5d5a1a/
├── TASK.md              →  ~/.hermes/personal/tasks/5d5a1a/task.md
├── TASK_MEMORY.md       →  ~/.hermes/personal/tasks/5d5a1a/memory.md
├── .hermes-task.json    →  ~/.hermes/personal/tasks/5d5a1a/meta.json
├── input/               ← REQUIREMENTS.md + images/
└── output/              ← all generated files
```

Migration commands:
```bash
# Create per-hash personal dir + symlinks
python3 manage_task.py init 5d5a1a

# Move user source files to input/
mkdir -p input && mv REQUIREMENTS.md input/ && mv images/ input/

# Move generated files to output/
mkdir -p output && mv RECORDING.md COMPOSITING.md IMAGE_SLIDESHOW.md output/
mv tts-*/ image-slideshow-*/ subtitle-gen-*/ browser-video-recording-*/ output/

# Verify clean worked
python3 pipeline.py --clean  # only removes output/, leaves input/ + symlinks

# Re-export (now clean, no output/ in archive)
python3 manage_task.py export 5d5a1a
# → tar.gz contains: input/ + personal-tasks/5d5a1a/ only
```

## Lessons

- When you discover TASK.md is missing: regenerate IMMEDIATELY, don't defer
- Always verify recovered TASK.md against the governing skill's phase template
- Symlink for TASK.md + .hermes-task.json prevents permanent loss from cleanup
- Pipeline cleanup MUST use output/ boundary, never exclusion-based deletion
- For tasks with a hash, `manage_task.py relink <hash>` is the fastest recovery path
- `manage_task.py init <hash>` creates all three symlinks in one command
