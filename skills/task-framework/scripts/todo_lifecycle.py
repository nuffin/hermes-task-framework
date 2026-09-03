#!/usr/bin/env python3
"""TASK.md TODO intake and deterministic scope routing.

TODOs are intentionally not checklist items: they are discovered requirements
which must be decomposed, routed, cancelled, or blocked before a task can be
considered complete.
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

STATUSES = {"open", "decomposed", "routed", "cancelled", "blocked"}
SCOPES = {"open", "continuous", "nested", "top-level", "cancelled", "blocked"}
_TABLE_HEADER = "| ID | Requirement | Source | Timestamp | Status | Scope decision | Routed task / checklist |"
_TABLE_SEPARATOR = "|---|---|---|---|---|---|---|"


def _section(text: str) -> tuple[int, int, list[str]]:
    match = re.search(r"^## TODO\s*\n(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
    if not match:
        return -1, -1, []
    return match.start(1), match.end(1), match.group(1).splitlines()


def _split_row(line: str) -> list[str]:
    cells, current = [], []
    raw = line.strip().strip("|")
    index = 0
    while index < len(raw):
        char = raw[index]
        if char == "\\" and index + 1 < len(raw) and raw[index + 1] == "|":
            current.append("|"); index += 2; continue
        if char == "|":
            cells.append("".join(current).strip()); current = []
        else:
            current.append(char)
        index += 1
    cells.append("".join(current).strip())
    return cells


def parse_todos(text: str) -> list[dict]:
    """Parse TODO table rows, tolerating omitted optional trailing cells."""
    _, _, lines = _section(text)
    result = []
    for line in lines:
        if not line.strip().startswith("|") or "---" in line:
            continue
        cells = _split_row(line)
        if len(cells) < 6 or cells[0].lower() in {"id", "#"}:
            continue
        result.append({
            "id": cells[0], "requirement": cells[1], "source": cells[2],
            "timestamp": cells[3], "status": cells[4].lower(),
            "scope": cells[5].lower(), "route": cells[6] if len(cells) > 6 else "",
        })
    return result


def validate_todos(text: str) -> list[str]:
    """Return validation errors; unresolved TODOs are valid, silently completed are not."""
    errors = []
    start, end, _ = _section(text)
    if start < 0:
        return errors
    todos = parse_todos(text)
    _, _, raw_lines = _section(text)
    for line in raw_lines:
        if line.strip().startswith("|") and "---" not in line and len(_split_row(line)) < 7:
            errors.append("malformed TODO table row: " + line.strip())
    seen = set()
    for item in todos:
        if not item["id"] or item["id"] in seen:
            errors.append(f"duplicate or empty TODO id: {item['id']!r}")
        seen.add(item["id"])
        for key in ("requirement", "source", "timestamp"):
            if not item[key]:
                errors.append(f"TODO {item['id']} missing {key}")
        if item["status"] not in STATUSES:
            errors.append(f"TODO {item['id']} has invalid status: {item['status']}")
        if item["scope"] not in SCOPES:
            errors.append(f"TODO {item['id']} has invalid scope decision: {item['scope']}")
        if item["status"] in {"decomposed", "routed", "cancelled", "blocked"} and not item["route"]:
            errors.append(f"TODO {item['id']} finalized without route/outcome")
        if item["status"] == "open" and item["scope"] != "open":
            errors.append(f"TODO {item['id']} open status requires scope decision open")
    return errors


def _render_row(item: dict) -> str:
    values = [item[k].replace("|", "\\|") for k in ("id", "requirement", "source", "timestamp", "status", "scope", "route")]
    return "| " + " | ".join(values) + " |"


def _ensure_section(text: str) -> str:
    if re.search(r"^## TODO\s*$", text, re.MULTILINE):
        return text
    marker = re.search(r"^## Checklist\s*$", text, re.MULTILINE)
    block = "## TODO\n\n" + _TABLE_HEADER + "\n" + _TABLE_SEPARATOR + "\n\n"
    return text[:marker.start()] + block + text[marker.start():] if marker else text.rstrip() + "\n\n" + block


def _replace_rows(text: str, todos: list[dict]) -> str:
    text = _ensure_section(text)
    start, end, lines = _section(text)
    body = "\n" + _TABLE_HEADER + "\n" + _TABLE_SEPARATOR
    if todos:
        body += "\n" + "\n".join(_render_row(item) for item in todos)
    body += "\n\n"
    return text[:start] + body + text[end:]


def add_todo(task_dir: str | Path, requirement: str, source: str) -> dict:
    path = Path(task_dir) / "TASK.md"
    text = path.read_text(encoding="utf-8")
    todos = parse_todos(text)
    identifier = f"todo-{len(todos) + 1}"
    while any(item["id"] == identifier for item in todos):
        identifier = f"todo-{len(todos) + 2}"
    item = {"id": identifier, "requirement": requirement, "source": source,
            "timestamp": datetime.now().isoformat(timespec="seconds"), "status": "open", "scope": "open", "route": ""}
    path.write_text(_replace_rows(text, todos + [item]), encoding="utf-8")
    return item


def update_todo(task_dir: str | Path, todo_id: str, scope: str, outcome: str) -> dict:
    if scope not in {"continuous", "nested", "top-level"}:
        raise ValueError("scope must be continuous, nested, or top-level")
    path = Path(task_dir) / "TASK.md"
    text = path.read_text(encoding="utf-8")
    todos = parse_todos(text)
    for item in todos:
        if item["id"] == todo_id:
            if item["status"] != "open":
                raise ValueError(f"TODO {todo_id} is already {item['status']}")
            item["scope"], item["status"], item["route"] = scope, "decomposed" if scope == "continuous" else "routed", outcome
            updated = _replace_rows(text, todos)
            if scope == "continuous":
                checklist = re.search(r"(^## Checklist\s*$.*?)(?=^## |\Z)", updated, re.MULTILINE | re.DOTALL)
                phase = f"- [ ] TODO {todo_id} — {outcome}\n"
                if checklist:
                    updated = updated[:checklist.end()] + phase + updated[checklist.end():]
                else:
                    updated += "\n## Checklist\n\n" + phase
            path.write_text(updated, encoding="utf-8")
            return item
    raise KeyError(f"TODO not found: {todo_id}")


def set_terminal(task_dir: str | Path, todo_id: str, status: str, outcome: str) -> dict:
    if status not in {"cancelled", "blocked"} or not outcome:
        raise ValueError("terminal TODO status must be cancelled or blocked with an outcome")
    path = Path(task_dir) / "TASK.md"
    text = path.read_text(encoding="utf-8")
    todos = parse_todos(text)
    for item in todos:
        if item["id"] == todo_id:
            if item["status"] != "open":
                raise ValueError(f"TODO {todo_id} is already {item['status']}")
            item["status"], item["scope"], item["route"] = status, status, outcome
            path.write_text(_replace_rows(text, todos), encoding="utf-8")
            return item
    raise KeyError(f"TODO not found: {todo_id}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_dir")
    sub = parser.add_subparsers(dest="command", required=True)
    add = sub.add_parser("add"); add.add_argument("requirement"); add.add_argument("--source", required=True)
    route = sub.add_parser("route"); route.add_argument("todo_id"); route.add_argument("scope", choices=("continuous", "nested", "top-level")); route.add_argument("outcome")
    terminal = sub.add_parser("terminal"); terminal.add_argument("todo_id"); terminal.add_argument("status", choices=("cancelled", "blocked")); terminal.add_argument("outcome")
    args = parser.parse_args()
    try:
        if args.command == "add": result = add_todo(args.task_dir, args.requirement, args.source)
        elif args.command == "route": result = update_todo(args.task_dir, args.todo_id, args.scope, args.outcome)
        else: result = set_terminal(args.task_dir, args.todo_id, args.status, args.outcome)
        print(result)
        return 0
    except (OSError, KeyError, ValueError) as exc:
        print(str(exc), file=sys.stderr); return 1

if __name__ == "__main__":
    raise SystemExit(main())
