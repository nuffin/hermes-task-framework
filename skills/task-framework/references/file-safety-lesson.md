# File Safety Lesson — 50MB PPT Loss (2026-06-02)

## What happened

A 50MB PPT file (`灵泽——心脑血管主动健康示范（5.18）.pptx`) was lost during `task_inbox_accept`. The `mv` command appeared to succeed (no error output, `ls -la` immediately after showed the file at the destination), but the file was later found to be gone — neither at source nor destination.

## Root cause

`mv` with Chinese filenames across a shell heredoc boundary can silently fail due to encoding/path resolution issues. **No error message was produced** — the `mv` appeared successful but the file never actually arrived.

## The fix

Never use `mv` for file moves. Always use a two-step approach:

1. **Step 1 — Create hard link (or copy)**
   - Same filesystem: `ln <src> <dst>` (instant, no space cost)
   - Cross-filesystem or symlink: `cp <src> <dst>` (slower but safe)

2. **Step 2 — Verify then delete**
   ```
   ls -la <dst>/ && rm -rf <src>
   ```
   The `&&` ensures the delete only runs if verification succeeds.

## Verification checklist after ANY file move

```bash
# 1. Confirm destination exists
ls -la <dst>/        # must show the file
# 2. Check file size matches
ls -l <dst>/<file>   # compare with expected size
# 3. Only then remove source
rm -rf <src>
```

## Why this matters for Hermes agents

Terminal commands may produce false positives — an `mv` that prints no error can still fail silently. The agent's shell session, encoding context, and CWD may differ from what the command expects. Two-step ln/cp+rm with explicit ls verification eliminates this class of bug.
