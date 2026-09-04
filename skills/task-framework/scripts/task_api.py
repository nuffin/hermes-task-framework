#!/usr/bin/env python3
"""Stable JSON interface for task-framework consumers and adapters."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import manage_task
import todo_lifecycle


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
    if candidate.is_dir() and manage_task._is_contained_task_dir(str(candidate)):
        return candidate.resolve()
    all_paths = [Path(value).resolve() for value in manage_task._find_discovered_task_dirs()]
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
        "todos": todo_lifecycle.parse_todos(task_text),
        "todo_validation_errors": todo_lifecycle.validate_todos(task_text),
        "metadata": metadata,
    }


def command_describe(identifier: str) -> dict:
    return describe_path(resolve(identifier))


def command_reconcile(identifier: str, result_json: str) -> dict:
    """Reconcile one returned L1 result; safe to retry with same result_id."""
    return todo_lifecycle.reconcile_return(resolve(identifier), json.loads(result_json))


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


def _write_metadata(metadata_path: Path, metadata: dict) -> None:
    temporary = metadata_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(metadata_path)


def command_set_extension(identifier: str, namespace: str, key: str, value_json: str) -> dict:
    task_dir = resolve(identifier)
    metadata_path = task_dir / ".hermes-task.json"
    metadata = json.loads(read_text(metadata_path) or "{}")
    extensions = metadata.setdefault("extensions", {})
    namespace_data = extensions.setdefault(namespace, {})
    namespace_data[key] = json.loads(value_json)
    _write_metadata(metadata_path, metadata)
    manage_task._run_update_index()
    return {"path": str(task_dir), "namespace": namespace, "key": key, "value": namespace_data[key]}


def _require_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _validate_remote_receipt(task_dir: Path, metadata: dict, receipt: object) -> dict:
    if not isinstance(receipt, dict):
        raise ValueError("remote dispatch receipt must be an object")
    task_hash = _require_string(receipt.get("task_hash"), "task_hash")
    expected_hash = metadata.get("hash") or manage_task._task_hash_from_dir(str(task_dir))
    if task_hash != expected_hash:
        raise ValueError("task_hash does not match the resolved task")
    for field in ("controller_node", "executor_node", "dispatch_id", "tmux_session", "tmux_window", "task_dir", "executor_profile"):
        _require_string(receipt.get(field), field)
    if not Path(receipt["task_dir"]).is_absolute():
        raise ValueError("task_dir must be an absolute path")
    if receipt["tmux_window"] != f"task-{task_hash}":
        raise ValueError("tmux_window must equal task-<task_hash>")
    if receipt.get("status") != "dispatched":
        raise ValueError("remote dispatch receipt status must be dispatched")
    return receipt


def command_set_remote_dispatch(identifier: str, receipt_json: str) -> dict:
    task_dir = resolve(identifier)
    metadata_path = task_dir / ".hermes-task.json"
    metadata = json.loads(read_text(metadata_path) or "{}")
    receipt = _validate_remote_receipt(task_dir, metadata, json.loads(receipt_json))
    namespace = metadata.setdefault("extensions", {}).setdefault("remote_execution", {})
    existing = namespace.get("receipt")
    if existing is not None:
        if existing == receipt:
            return {"path": str(task_dir), "receipt": existing, "idempotent": True}
        raise ValueError("remote dispatch receipt already exists with a different identity")
    namespace["receipt"] = receipt
    _write_metadata(metadata_path, metadata)
    manage_task._run_update_index()
    return {"path": str(task_dir), "receipt": receipt, "idempotent": False}


def _validate_remote_result(metadata: dict, manifest: object) -> dict:
    if not isinstance(manifest, dict):
        raise ValueError("remote result manifest must be an object")
    receipt = metadata.get("extensions", {}).get("remote_execution", {}).get("receipt")
    if not isinstance(receipt, dict):
        raise ValueError("remote dispatch receipt is required before recording a result")
    for field in ("task_hash", "dispatch_id", "executor_node"):
        if manifest.get(field) != receipt.get(field):
            raise ValueError(f"{field} does not match remote dispatch receipt")
    source_commit = _require_string(manifest.get("source_commit"), "source_commit")
    if not re.fullmatch(r"[0-9a-f]{7,64}", source_commit):
        raise ValueError("source_commit must be a lowercase hexadecimal Git OID")
    if manifest.get("status") not in {"pending_review", "done"}:
        raise ValueError("remote result status must be pending_review or done")
    outputs = manifest.get("outputs")
    if not isinstance(outputs, list):
        raise ValueError("outputs must be a list")
    names: set[str] = set()
    for output in outputs:
        if not isinstance(output, dict):
            raise ValueError("each output must be an object")
        name = _require_string(output.get("name"), "output name")
        if name in names:
            raise ValueError("output names must be unique")
        names.add(name)
        path = _require_string(output.get("path"), "output path")
        if Path(path).is_absolute() or ".." in Path(path).parts:
            raise ValueError("output path must be a safe task-relative path")
        if not isinstance(output.get("bytes"), int) or output["bytes"] < 0:
            raise ValueError("output bytes must be a non-negative integer")
        if not isinstance(output.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", output["sha256"]):
            raise ValueError("output sha256 must be a lowercase SHA-256 digest")
    return manifest


def command_record_remote_result(identifier: str, manifest_json: str) -> dict:
    task_dir = resolve(identifier)
    metadata_path = task_dir / ".hermes-task.json"
    metadata = json.loads(read_text(metadata_path) or "{}")
    manifest = _validate_remote_result(metadata, json.loads(manifest_json))
    namespace = metadata.setdefault("extensions", {}).setdefault("remote_execution", {})
    existing = namespace.get("result")
    if existing is not None:
        if existing == manifest:
            return {"path": str(task_dir), "result": existing, "idempotent": True}
        raise ValueError("remote result manifest already exists with different content")
    namespace["result"] = manifest
    _write_metadata(metadata_path, metadata)
    manage_task._run_update_index()
    return {"path": str(task_dir), "result": manifest, "idempotent": False}


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

    reconcile_parser = commands.add_parser("reconcile")
    reconcile_parser.add_argument("identifier")
    reconcile_parser.add_argument("result_json", help="JSON L1 return payload with stable result_id")

    get_extension_parser = commands.add_parser("get-extension")
    get_extension_parser.add_argument("identifier")
    get_extension_parser.add_argument("namespace")
    get_extension_parser.add_argument("key", nargs="?")
    set_extension_parser = commands.add_parser("set-extension")
    set_extension_parser.add_argument("identifier")
    set_extension_parser.add_argument("namespace")
    set_extension_parser.add_argument("key")
    set_extension_parser.add_argument("value_json")
    remote_dispatch_parser = commands.add_parser("set-remote-dispatch")
    remote_dispatch_parser.add_argument("identifier")
    remote_dispatch_parser.add_argument("receipt_json")
    remote_result_parser = commands.add_parser("record-remote-result")
    remote_result_parser.add_argument("identifier")
    remote_result_parser.add_argument("manifest_json")
    args = parser.parse_args()
    try:
        if args.command == "describe":
            result = command_describe(args.identifier)
        elif args.command == "search":
            result = command_search(args.query)
        elif args.command == "get-meta":
            result = command_get_meta(args.identifier, args.key)
        elif args.command == "reconcile":
            result = command_reconcile(args.identifier, args.result_json)
        elif args.command == "get-extension":
            result = command_get_extension(args.identifier, args.namespace, args.key)
        elif args.command == "set-extension":
            result = command_set_extension(args.identifier, args.namespace, args.key, args.value_json)
        elif args.command == "set-remote-dispatch":
            result = command_set_remote_dispatch(args.identifier, args.receipt_json)
        else:
            result = command_record_remote_result(args.identifier, args.manifest_json)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (FileNotFoundError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
