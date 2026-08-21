#!/usr/bin/env python3
"""Safely inspect and synchronize a Git-backed task root."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

TASK_SCRIPTS = Path(__file__).resolve().parents[2] / "task-framework" / "scripts"
sys.path.insert(0, str(TASK_SCRIPTS))
import manage_task  # pyright: ignore[reportMissingImports]  # noqa: E402


def git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=check,
    )


def resolve_root(raw: str | None) -> Path:
    return Path(raw or manage_task.TASKS_ROOT).expanduser().resolve()


def repository_status(root: Path) -> dict:
    inside = git(root, "rev-parse", "--is-inside-work-tree", check=False)
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        raise ValueError(f"not a Git repository: {root}")
    branch = git(root, "branch", "--show-current").stdout.strip()
    porcelain = git(root, "status", "--porcelain").stdout.splitlines()
    remotes = git(root, "remote").stdout.splitlines()
    return {"root": str(root), "branch": branch, "clean": not porcelain, "changes": porcelain, "remotes": remotes}


def divergence(root: Path, remote: str, branch: str) -> tuple[int, int]:
    process = git(root, "rev-list", "--left-right", "--count", f"HEAD...{remote}/{branch}", check=False)
    if process.returncode != 0:
        raise ValueError(process.stderr.strip() or f"cannot compare {remote}/{branch}")
    left, right = process.stdout.strip().split()
    return int(left), int(right)


def verify_preconditions(root: Path, remote: str, branch: str, execute: bool) -> dict:
    if not execute:
        raise ValueError("refusing mutation without --execute")
    status = repository_status(root)
    if not status["clean"]:
        raise ValueError("task root has uncommitted changes")
    if remote not in status["remotes"]:
        raise ValueError(f"remote not configured: {remote}")
    if not branch:
        raise ValueError("branch is required")
    return status


def pull(root: Path, remote: str, branch: str, execute: bool) -> dict:
    status = verify_preconditions(root, remote, branch, execute)
    fetch = git(root, "fetch", remote, branch, check=False)
    if fetch.returncode != 0:
        raise ValueError(fetch.stderr.strip() or "git fetch failed")
    local_ahead, remote_ahead = divergence(root, remote, branch)
    if local_ahead and remote_ahead:
        raise ValueError("task root has diverged; manual reconciliation required")
    if remote_ahead:
        merge = git(root, "merge", "--ff-only", f"{remote}/{branch}", check=False)
        if merge.returncode != 0:
            raise ValueError(merge.stderr.strip() or "fast-forward failed")
    manage_task._run_update_index()
    return {"action": "pull", "before": status, "local_ahead": local_ahead, "remote_ahead": remote_ahead}


def push(root: Path, remote: str, branch: str, execute: bool) -> dict:
    status = verify_preconditions(root, remote, branch, execute)
    fetch = git(root, "fetch", remote, branch, check=False)
    if fetch.returncode != 0:
        raise ValueError(fetch.stderr.strip() or "git fetch failed")
    local_ahead, remote_ahead = divergence(root, remote, branch)
    if remote_ahead:
        raise ValueError("remote is ahead or diverged; pull/reconcile before push")
    process = git(root, "push", remote, f"HEAD:{branch}", check=False)
    if process.returncode != 0:
        raise ValueError(process.stderr.strip() or "git push failed")
    return {"action": "push", "before": status, "local_ahead": local_ahead, "remote_ahead": remote_ahead}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("status", "pull", "push"):
        command = commands.add_parser(name)
        command.add_argument("--tasks-root")
        command.add_argument("--remote", default="origin")
        command.add_argument("--branch")
        if name != "status":
            command.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    root = resolve_root(args.tasks_root)
    try:
        if args.command == "status":
            result = repository_status(root)
        elif args.command == "pull":
            result = pull(root, args.remote, args.branch or "", args.execute)
        else:
            result = push(root, args.remote, args.branch or "", args.execute)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
