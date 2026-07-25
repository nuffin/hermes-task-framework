# TASK.md Recovery: 5d5a1a (2026-06-11)

## Scenario

Agent asked to find TASK.md for task `5d5a1a`. It didn't exist — deleted weeks earlier by exclusion-based cleanup. Only CHANGELOG.md and the phase directories remained.

## Process

1. **Identify task type** — scanned task directory. Found REQUIREMENTS.md + RECORDING.md + COMPOSITING.md → video production pipeline task.
2. **Load governing skill** — `skill_view('browser-screen-record-task')` for the phase template.
3. **Map evidence to phases** — cross-referenced phase directories (tts-6d3e4c/, browser-video-recording-6d3e4c/, compositing-6d3e4c/) against the skill's phase table.
4. **Read CHANGELOG.md** — confirmed final output: 174.1s / 5.8MB, all phases complete.
5. **Write TASK.md** following skill's template — used the correct phase decomposition (1a/b/c parallel → 2 timeline-composer → 3 recording → 4 composite), matching `browser-screen-record-task`'s defined phases.
6. **Verify** — checked output files exist, status = completed.

## Key Lesson

Phase structure must come from the domain skill, not guessed from memory or prior conversation. When I initially wrote the TASK.md, I used my own phase order (missing timeline-composer, wrong parallel grouping). The user corrected: "你可以参考 browser-screen-record-task 这个 skill，看看你的 phases 分解的对不对".

## Recovery from task directory (future)

If TASK.md was in the task directory:
```bash
# Direct reconstruction from CHANGELOG.md + artifacts:
# Use the recovery procedure in Step 1-6 above.
```
No content reconstruction from symlinks needed — all files live directly in the task directory.
