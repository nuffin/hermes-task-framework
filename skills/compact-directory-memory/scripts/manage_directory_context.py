#!/usr/bin/env python3
"""Create and verify flat or hierarchical directory context."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SUBSYSTEM_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

ROOT_MEMORY = """Entity context is managed by compact-directory-memory.

§

Subsystem context index is stored under `memories/`.
"""

ROOT_CHANGELOG = """# CHANGELOG.md

Append chronological cross-session context entries.
"""

SUBSYSTEM_MEMORY = """Subsystem: `{subsystem}`.

§

Repository/path: <fill when known>.

§

Responsibilities and boundaries: <fill when known>.
"""

SUBSYSTEM_CHANGELOG = """# {subsystem} — CHANGELOG.md

Append chronological subsystem operations, decisions, verification, blockers, and next steps.
"""


def ensure_file(path: Path, content: str) -> bool:
    if path.exists():
        return False
    path.write_text(content, encoding="utf-8")
    return True


def validate_subsystem(name: str) -> None:
    if not SUBSYSTEM_RE.fullmatch(name):
        raise ValueError(f"invalid subsystem name: {name!r}; use lowercase kebab-case")


def init(entity_dir: Path, subsystems: list[str]) -> int:
    if not entity_dir.is_dir():
        print(f"ERROR: entity directory not found: {entity_dir}", file=sys.stderr)
        return 2
    created: list[Path] = []
    if ensure_file(entity_dir / "MEMORY.md", ROOT_MEMORY):
        created.append(entity_dir / "MEMORY.md")
    if ensure_file(entity_dir / "CHANGELOG.md", ROOT_CHANGELOG):
        created.append(entity_dir / "CHANGELOG.md")
    memories = entity_dir / "memories"
    memories.mkdir(exist_ok=True)
    for subsystem in subsystems:
        validate_subsystem(subsystem)
        directory = memories / subsystem
        directory.mkdir(exist_ok=True)
        memory_file = directory / "MEMORY.md"
        changelog_file = directory / "CHANGELOG.md"
        if ensure_file(memory_file, SUBSYSTEM_MEMORY.format(subsystem=subsystem)):
            created.append(memory_file)
        if ensure_file(changelog_file, SUBSYSTEM_CHANGELOG.format(subsystem=subsystem)):
            created.append(changelog_file)
    for path in created:
        print(f"created {path.relative_to(entity_dir)}")
    print(f"initialized directory context: subsystems={len(subsystems)}")
    return verify(entity_dir)


def verify(entity_dir: Path) -> int:
    errors: list[str] = []
    for required in ("MEMORY.md", "CHANGELOG.md"):
        if not (entity_dir / required).is_file():
            errors.append(f"missing root file: {required}")
    memories = entity_dir / "memories"
    if not memories.is_dir():
        errors.append("missing directory: memories/")
    else:
        for directory in sorted(path for path in memories.iterdir() if path.is_dir()):
            try:
                validate_subsystem(directory.name)
            except ValueError as exc:
                errors.append(str(exc))
            for required in ("MEMORY.md", "CHANGELOG.md"):
                if not (directory / required).is_file():
                    errors.append(f"missing subsystem file: memories/{directory.name}/{required}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    subsystem_count = sum(1 for path in memories.iterdir() if path.is_dir())
    print(f"verified directory context: root files OK, subsystems={subsystem_count}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init_parser = commands.add_parser("init")
    init_parser.add_argument("entity_dir", type=Path)
    init_parser.add_argument("subsystems", nargs="*")
    verify_parser = commands.add_parser("verify")
    verify_parser.add_argument("entity_dir", type=Path)
    args = parser.parse_args()
    entity_dir = args.entity_dir.expanduser().resolve()
    try:
        if args.command == "init":
            return init(entity_dir, args.subsystems)
        return verify(entity_dir)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
