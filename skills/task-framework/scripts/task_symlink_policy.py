"""Portable, task-scoped symlink policy for task-framework."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

CANONICAL_TASK_FILES = frozenset({"TASK.md", "README.md", "MEMORY.md", "CHANGELOG.md", ".hermes-task.json"})
ROOT_INDEX_FILES = frozenset({"README.md", "TASKS.md"})


def _contained(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _entry(path: Path, task_root: Path) -> dict:
    relative = path.relative_to(task_root).as_posix()
    raw_target = os.readlink(path)
    raw_path = Path(raw_target)
    resolved = (path.parent / raw_path).resolve(strict=False)
    result = {
        "path": relative,
        "target": raw_target,
        "resolved": str(resolved),
        "allowed": False,
        "reason": "",
    }
    if raw_path.is_absolute():
        result["reason"] = "absolute target"
    elif not resolved.exists():
        result["reason"] = "missing target"
    elif not _contained(resolved, task_root):
        result["reason"] = "target escapes task root"
    elif len(path.relative_to(task_root).parts) == 1 and path.name in CANONICAL_TASK_FILES:
        result["reason"] = "canonical task file must be regular"
    else:
        result["allowed"] = True
        result["reason"] = "relative contained target"
    return result


def inspect_task(task_root: Path) -> dict:
    root = task_root.resolve(strict=True)
    entries = [_entry(path, root) for path in sorted(root.rglob("*")) if path.is_symlink()]
    rejected = [entry for entry in entries if not entry["allowed"]]
    return {"scope": "task", "root": str(root), "ok": not rejected, "symlinks": entries, "rejected": rejected}


def _eligible_symlinks(tasks_root: Path) -> list[tuple[Path, Path]]:
    """Return task-owned symlinks Git may checkpoint, never ignored runtime trees."""
    root = tasks_root.resolve(strict=True)
    try:
        output = subprocess.check_output(
            ["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            text=False,
        )
        candidates = [root / item.decode(errors="surrogateescape") for item in output.split(b"\0") if item]
    except (OSError, subprocess.CalledProcessError):
        candidates = list(root.rglob("*"))
    entries: list[tuple[Path, Path]] = []
    for path in candidates:
        if not path.is_symlink():
            continue
        relative = path.relative_to(root)
        if not relative.parts or not relative.parts[0].startswith("2"):
            continue
        task_root = root / relative.parts[0]
        if task_root.is_dir() and not task_root.is_symlink():
            entries.append((path, task_root))
    return entries


def inspect_tasks_root(tasks_root: Path) -> dict:
    root = tasks_root.resolve(strict=True)
    entries: list[dict] = []
    for name in ROOT_INDEX_FILES:
        candidate = root / name
        if candidate.is_symlink():
            entries.append({
                "path": name,
                "target": os.readlink(candidate),
                "resolved": str((candidate.parent / os.readlink(candidate)).resolve(strict=False)),
                "allowed": False,
                "reason": "root index must be regular",
            })
    for path, task_root in _eligible_symlinks(root):
        entries.append(_entry(path, task_root))
    rejected = [entry for entry in entries if not entry["allowed"]]
    return {"scope": "tasks-root", "root": str(root), "ok": not rejected, "symlinks": entries, "rejected": rejected}


def require_tasks_root(tasks_root: Path) -> dict:
    report = inspect_tasks_root(tasks_root)
    if report["rejected"]:
        details = "; ".join(f"{entry['path']}: {entry['reason']}" for entry in report["rejected"])
        raise ValueError("task symlink policy rejected: " + details)
    return report
