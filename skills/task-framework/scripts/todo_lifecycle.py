#!/usr/bin/env python3
"""TASK.md TODO intake and deterministic scope routing.

TODOs are intentionally not checklist items: they are discovered requirements
which must be decomposed, routed, cancelled, or blocked before a task can be
considered complete.
"""
from __future__ import annotations

import argparse
import json
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


def _has_unfinished_checklist(text: str) -> bool:
    """Return true when a non-BREAK checklist item is still pending."""
    return any(
        re.match(r"^\s*- \[ \]", line) and not line.strip().startswith("- [ ] BREAK:")
        for line in text.splitlines()
    )


def reconcile_return(task_dir: str | Path, result: dict, classifier=None) -> dict:
    """Reconcile one returned L1 result and select dependency-ready work.

    The stable ``result_id`` makes processing idempotent. This planner does not
    dispatch workers; callers execute returned routes and invoke it once per
    result. A blocked result is terminal, while unresolved TODOs remain open.
    """
    if not isinstance(result, dict) or not result.get("result_id"):
        raise ValueError("result_id is required for idempotent reconciliation")
    result_id = str(result["result_id"])
    state_path = Path(task_dir) / ".todo-continuation.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid continuation state: {exc}") from exc
    processed = set(state.get("processed_results", []))
    if result_id in processed:
        return {"outcome": "IDEMPOTENT", "result_id": result_id, "routes": []}
    status = str(result.get("status", "completed")).lower()
    if status not in {"completed", "blocked"}:
        raise ValueError("L1 result status must be completed or blocked")
    discovered = result.get("discovered_todos", []) or []
    if not isinstance(discovered, list):
        raise ValueError("discovered_todos must be a list")
    text = (Path(task_dir) / "TASK.md").read_text(encoding="utf-8")
    existing = parse_todos(text)
    by_key = {(item["requirement"], item["source"]): item for item in existing}
    for row in discovered:
        if not isinstance(row, dict) or not row.get("requirement"):
            raise ValueError("each discovered TODO needs requirement")
        source = str(row.get("source", f"L1 {result_id}"))
        key = (str(row["requirement"]), source)
        if key not in by_key:
            by_key[key] = add_todo(task_dir, key[0], key[1])
    if status == "blocked":
        processed.add(result_id)
        _write_continuation_state(state_path, processed)
        return {"outcome": "HARD_BLOCK", "result_id": result_id,
                "reason": result.get("reason", "L1 reported a hard block"), "routes": []}
    checklist = "\\n".join(line for line in text.splitlines() if line.startswith("- [x]"))
    routes = []
    for row in discovered:
        source = str(row.get("source", f"L1 {result_id}"))
        item = by_key[(str(row["requirement"]), source)]
        if item["status"] != "open":
            continue
        dependencies = [str(value) for value in row.get("depends_on", [])]
        if dependencies and not all(re.search(re.escape(dep), checklist, re.IGNORECASE) for dep in dependencies):
            continue
        scope = classifier(item) if classifier else row.get("scope")
        if scope in {"continuous", "nested", "top-level"}:
            outcome = str(row.get("outcome") or {"continuous": "next checklist phase", "nested": "child task required", "top-level": "independent task required"}[scope])
            update_todo(task_dir, item["id"], scope, outcome)
            routes.append({"todo_id": item["id"], "scope": scope, "outcome": outcome})
    current_text = (Path(task_dir) / "TASK.md").read_text(encoding="utf-8")
    remaining = [item for item in parse_todos(current_text) if item["status"] == "open"]
    checklist_pending = _has_unfinished_checklist(current_text)
    processed.add(result_id)
    _write_continuation_state(state_path, processed)
    if (remaining or checklist_pending) and not routes:
        return {"outcome": "CONTINUE_WAITING", "result_id": result_id, "routes": [], "todo_ids": [item["id"] for item in remaining], "checklist_pending": checklist_pending}
    return {"outcome": "CONTINUE" if (remaining or checklist_pending or routes) else "COMPLETE", "result_id": result_id, "routes": routes, "checklist_pending": checklist_pending}


def _write_continuation_state(path: Path, processed: set[str]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps({"processed_results": sorted(processed)}, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


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
