#!/usr/bin/env python3
"""Stable JSON interface for task-framework consumers and adapters."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import manage_task


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def section(text: str, heading: str) -> str:
    match = re.search(
        rf"^## {re.escape(heading)}\s*\n+(.*?)(?=^## |\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    return match.group(1).strip() if match else ""


def title(text: str) -> str:
    match = re.search(r"^# Task:\s*(.+)$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def parse_checklist(text: str) -> list[dict]:
    items: list[dict] = []
    for line in section(text, "Checklist").splitlines():
        match = re.match(r"^- \[([ xX])\]\s*(.+)$", line.strip())
        if not match:
            continue
        item_text = match.group(2).strip()
        phase_match = re.search(r"\b(Phase\s+[A-Za-z0-9_.-]+)", item_text, re.IGNORECASE)
        skill_match = re.search(r"\(([^)]+)\)", item_text)
        phase = phase_match.group(1) if phase_match else None
        dependencies = sorted(set(re.findall(r"Phase\s+[A-Za-z0-9_.-]+", item_text, re.IGNORECASE)))
        dependencies = [value for value in dependencies if value.lower() != str(phase).lower()]
        upper = item_text.upper()
        items.append({
            "index": len(items),
            "checked": match.group(1).lower() == "x",
            "kind": "break" if upper.startswith(("BREAK:", "DONE:")) else "phase",
            "text": item_text,
            "phase": phase,
            "skill": skill_match.group(1) if skill_match else None,
            "depends_on": dependencies,
        })
    return items


def resolve(identifier: str) -> Path:
    if re.fullmatch(r"[a-z0-9]{6}", identifier):
        value = manage_task._find_task_dir_by_hash(identifier)
        if value:
            return Path(value).resolve()
    candidate = Path(identifier).expanduser()
    if candidate.is_dir():
        return candidate.resolve()
    all_paths = [Path(value).resolve() for value in manage_task._find_all_task_dirs()]
    exact = [path for path in all_paths if path.name == identifier]
    if not exact:
        for path in all_paths:
            task_text = read_text(path / "TASK.md")
            metadata = json.loads(read_text(path / ".hermes-task.json") or "{}")
            if identifier in {metadata.get("name"), title(task_text)}:
                exact.append(path)
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        raise ValueError(f"ambiguous task identifier {identifier!r}: {', '.join(path.name for path in exact)}")
    fuzzy = [path for path in all_paths if identifier.lower() in path.name.lower()]
    if len(fuzzy) == 1:
        return fuzzy[0]
    if len(fuzzy) > 1:
        raise ValueError(f"ambiguous task identifier {identifier!r}: {', '.join(path.name for path in fuzzy)}")
    raise FileNotFoundError(f"task not found: {identifier}")


def describe_path(task_dir: Path) -> dict:
    task_text = read_text(task_dir / "TASK.md")
    metadata_path = task_dir / ".hermes-task.json"
    metadata = json.loads(read_text(metadata_path) or "{}")
    return {
        "path": str(task_dir),
        "directory": task_dir.name,
        "hash": metadata.get("hash") or manage_task._task_hash_from_dir(str(task_dir)),
        "name": metadata.get("name") or title(task_text),
        "title": title(task_text),
        "status": section(task_text, "Status").splitlines()[0] if section(task_text, "Status") else "",
        "goal": section(task_text, "Goal").splitlines()[0] if section(task_text, "Goal") else "",
        "memory_layout": metadata.get("memory_layout", "flat"),
        "memory_root": metadata.get("memory_root"),
        "parent": {
            "hash": metadata.get("parent_hash"),
            "path": metadata.get("parent_path"),
        } if metadata.get("parent_hash") else None,
        "children": [
            {"hash": json.loads(read_text(Path(child) / ".hermes-task.json") or "{}").get("hash") or manage_task._task_hash_from_dir(child),
             "path": str(Path(child).resolve()), "name": Path(child).name}
            for child in manage_task._find_child_task_dirs(task_dir)
        ],
        "checklist": parse_checklist(task_text),
        "metadata": metadata,
    }


def command_describe(identifier: str) -> dict:
    return describe_path(resolve(identifier))


def command_search(query: str) -> list[dict]:
    terms = [item.lower() for item in query.split() if item.strip()]
    results = []
    for raw in manage_task._find_all_task_dirs():
        item = describe_path(Path(raw).resolve())
        haystack = " ".join(
            str(item.get(key, "")) for key in ("directory", "hash", "name", "title", "goal", "status")
        ).lower()
        if all(term in haystack for term in terms):
            results.append(item)
    return results


def command_get_meta(identifier: str, key: str | None) -> object:
    metadata = command_describe(identifier)["metadata"]
    if key is None:
        return metadata
    if key not in metadata:
        raise KeyError(f"metadata key not found: {key}")
    return metadata[key]


def command_get_extension(identifier: str, namespace: str, key: str | None) -> object:
    metadata = command_describe(identifier)["metadata"]
    extension = metadata.get("extensions", {}).get(namespace, {})
    if key is None:
        return extension
    if key not in extension:
        raise KeyError(f"extension key not found: {namespace}.{key}")
    return extension[key]


def command_set_extension(identifier: str, namespace: str, key: str, value_json: str) -> dict:
    task_dir = resolve(identifier)
    metadata_path = task_dir / ".hermes-task.json"
    metadata = json.loads(read_text(metadata_path) or "{}")
    extensions = metadata.setdefault("extensions", {})
    namespace_data = extensions.setdefault(namespace, {})
    namespace_data[key] = json.loads(value_json)
    temporary = metadata_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(metadata_path)
    manage_task._run_update_index()
    return {"path": str(task_dir), "namespace": namespace, "key": key, "value": namespace_data[key]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    describe_parser = commands.add_parser("describe")
    describe_parser.add_argument("identifier")
    search_parser = commands.add_parser("search")
    search_parser.add_argument("query")
    get_parser = commands.add_parser("get-meta")
    get_parser.add_argument("identifier")
    get_parser.add_argument("key", nargs="?")

    get_extension_parser = commands.add_parser("get-extension")
    get_extension_parser.add_argument("identifier")
    get_extension_parser.add_argument("namespace")
    get_extension_parser.add_argument("key", nargs="?")
    set_extension_parser = commands.add_parser("set-extension")
    set_extension_parser.add_argument("identifier")
    set_extension_parser.add_argument("namespace")
    set_extension_parser.add_argument("key")
    set_extension_parser.add_argument("value_json")
    args = parser.parse_args()
    try:
        if args.command == "describe":
            result = command_describe(args.identifier)
        elif args.command == "search":
            result = command_search(args.query)
        elif args.command == "get-meta":
            result = command_get_meta(args.identifier, args.key)
        elif args.command == "get-extension":
            result = command_get_extension(args.identifier, args.namespace, args.key)
        else:
            result = command_set_extension(args.identifier, args.namespace, args.key, args.value_json)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (FileNotFoundError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
