#!/usr/bin/env python3
"""Audit task closure and compare deterministic task manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

TASK_SCRIPTS = Path(__file__).resolve().parents[2] / "task-framework" / "scripts"
sys.path.insert(0, str(TASK_SCRIPTS))
import task_api  # pyright: ignore[reportMissingImports]  # noqa: E402
from task_symlink_policy import inspect_task  # pyright: ignore[reportMissingImports]  # noqa: E402

CANONICAL = ("TASK.md", "README.md", "MEMORY.md", "CHANGELOG.md", ".hermes-task.json")
RELATION_KEYS = ("dependencies", "related", "supersedes", "requires", "required_by")


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(root: Path) -> list[dict]:
    entries: list[dict] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if relative == ".git" or relative.startswith(".git/"):
            continue
        if path.is_symlink():
            entries.append({"path": relative, "type": "symlink", "target": os.readlink(path)})
        elif path.is_dir():
            entries.append({"path": relative, "type": "directory"})
        elif path.is_file():
            entries.append(
                {"path": relative, "type": "file", "size": path.stat().st_size, "sha256": file_hash(path)}
            )
    return entries


def relation_hashes(metadata: dict) -> list[str]:
    values: list[str] = []
    for key in RELATION_KEYS:
        raw = metadata.get(key, [])
        if isinstance(raw, list):
            values.extend(str(item) for item in raw if item)
    return sorted(set(values))


def audit(identifier: str) -> dict:
    description = task_api.command_describe(identifier)
    root = Path(description["path"])
    metadata = description["metadata"]
    errors: list[str] = []
    warnings: list[str] = []
    for name in CANONICAL:
        path = root / name
        if not path.is_file():
            errors.append(f"missing canonical file: {name}")
        elif path.stat().st_size == 0:
            errors.append(f"empty canonical file: {name}")
    memories = root / "memories"
    hierarchical = metadata.get("memory_layout") == "hierarchical" or memories.is_dir()
    subsystems: list[str] = []
    if hierarchical:
        if not memories.is_dir():
            errors.append("hierarchical metadata set but memories/ is missing")
        else:
            for directory in sorted(path for path in memories.iterdir() if path.is_dir()):
                subsystems.append(directory.name)
                for name in ("MEMORY.md", "CHANGELOG.md"):
                    if not (directory / name).is_file():
                        errors.append(f"incomplete subsystem context: memories/{directory.name}/{name}")
    outputs = metadata.get("outputs", {})
    if isinstance(outputs, dict):
        for name, raw_path in outputs.items():
            candidate = root / str(raw_path)
            if not candidate.exists():
                errors.append(f"named output does not resolve: {name} -> {raw_path}")
    unresolved: list[str] = []
    for task_hash in relation_hashes(metadata):
        try:
            task_api.command_describe(task_hash)
        except FileNotFoundError:
            unresolved.append(task_hash)
    if unresolved:
        errors.append(f"unresolved related task hashes: {', '.join(unresolved)}")
    for dirname in ("input", "output", "scripts"):
        if not (root / dirname).is_dir():
            warnings.append(f"missing standard directory: {dirname}/")
    symlinks = inspect_task(root)
    errors.extend(
        f"symlink policy: {entry['path']}: {entry['reason']}"
        for entry in symlinks["rejected"]
    )
    return {
        "task": description,
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "subsystems": subsystems,
        "relations": relation_hashes(metadata),
        "symlinks": symlinks,
        "manifest_entries": len(build_manifest(root)),
    }


def closure(identifier: str) -> dict:
    root = task_api.command_describe(identifier)
    queue = [root["hash"]]
    seen: dict[str, dict] = {}
    unresolved: list[str] = []
    while queue:
        current = queue.pop(0)
        if current in seen:
            continue
        try:
            item = task_api.command_describe(current)
        except FileNotFoundError:
            unresolved.append(current)
            continue
        seen[current] = item
        queue.extend(task_hash for task_hash in relation_hashes(item["metadata"]) if task_hash not in seen)
    return {"root": root["hash"], "tasks": list(seen.values()), "unresolved": sorted(set(unresolved))}


def post_flight(identifier: str) -> dict:
    description = task_api.command_describe(identifier)
    report = inspect_task(Path(description["path"]))
    return {
        "scope": "task",
        "phase": "post-flight",
        "task": {"hash": description["hash"], "path": description["path"]},
        "ok": report["ok"],
        "symlinks": report,
    }


def compare(source: Path, destination: Path) -> dict:
    source_manifest = build_manifest(source.resolve())
    destination_manifest = build_manifest(destination.resolve())
    source_map = {entry["path"]: entry for entry in source_manifest}
    destination_map = {entry["path"]: entry for entry in destination_manifest}
    missing = sorted(set(source_map) - set(destination_map))
    extra = sorted(set(destination_map) - set(source_map))
    changed = sorted(
        path for path in set(source_map) & set(destination_map) if source_map[path] != destination_map[path]
    )
    return {"equal": not missing and not extra and not changed, "missing": missing, "extra": extra, "changed": changed}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    audit_parser = commands.add_parser("audit")
    audit_parser.add_argument("identifier")
    closure_parser = commands.add_parser("closure")
    closure_parser.add_argument("identifier")
    symlinks_parser = commands.add_parser("symlinks")
    symlinks_parser.add_argument("identifier")
    post_flight_parser = commands.add_parser("post-flight")
    post_flight_parser.add_argument("identifier")
    manifest_parser = commands.add_parser("manifest")
    manifest_parser.add_argument("identifier")
    manifest_parser.add_argument("--output", type=Path)
    compare_parser = commands.add_parser("compare")
    compare_parser.add_argument("source", type=Path)
    compare_parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "audit":
            result = audit(args.identifier)
            code = 0 if result["ok"] else 1
        elif args.command == "closure":
            result = closure(args.identifier)
            code = 0 if not result["unresolved"] else 1
        elif args.command == "symlinks":
            description = task_api.command_describe(args.identifier)
            result = inspect_task(Path(description["path"]))
            code = 0 if result["ok"] else 1
        elif args.command == "post-flight":
            result = post_flight(args.identifier)
            code = 0 if result["ok"] else 1
        elif args.command == "manifest":
            root = Path(task_api.command_describe(args.identifier)["path"])
            result = build_manifest(root)
            if args.output:
                args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            code = 0
        else:
            result = compare(args.source, args.destination)
            code = 0 if result["equal"] else 1
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return code
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
