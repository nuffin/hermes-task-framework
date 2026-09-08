#!/usr/bin/env python3
"""Create and verify flat or hierarchical directory context."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SUBSYSTEM_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FRONTMATTER_START = "---\n"
FRONTMATTER_END = "---\n"

ROOT_MEMORY_BODY = """Entity context is managed by compact-directory-memory.

§

Subsystem context index is stored in this file's YAML frontmatter.
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


def render_root_memory(children: list[str], body: str) -> str:
    lines = ["---", "context_memory:", "  children:"]
    for subsystem in children:
        lines.extend(
            (
                f"    - id: {subsystem}",
                f"      memory: memories/{subsystem}/MEMORY.md",
                f"      changelog: memories/{subsystem}/CHANGELOG.md",
            )
        )
    lines.extend(("---", body))
    return "\n".join(lines)


def parse_root_memory(content: str) -> tuple[list[dict[str, str]], str]:
    """Parse the deliberately restricted canonical root index YAML format."""
    if not content.startswith(FRONTMATTER_START):
        raise ValueError("missing YAML frontmatter at top of root MEMORY.md")
    end = content.find(FRONTMATTER_END, len(FRONTMATTER_START))
    if end == -1:
        raise ValueError("unterminated YAML frontmatter in root MEMORY.md")
    yaml_lines = content[len(FRONTMATTER_START):end].splitlines()
    body = content[end + len(FRONTMATTER_END):]
    if yaml_lines[:2] != ["context_memory:", "  children:"]:
        raise ValueError("noncanonical root frontmatter: expected context_memory.children")

    children: list[dict[str, str]] = []
    index = 2
    while index < len(yaml_lines):
        if index + 2 >= len(yaml_lines):
            raise ValueError("noncanonical root frontmatter: incomplete child entry")
        id_match = re.fullmatch(r"    - id: ([^\s]+)", yaml_lines[index])
        memory_match = re.fullmatch(r"      memory: (\S+)", yaml_lines[index + 1])
        changelog_match = re.fullmatch(r"      changelog: (\S+)", yaml_lines[index + 2])
        if not (id_match and memory_match and changelog_match):
            raise ValueError("noncanonical root frontmatter: child entries require id, memory, changelog")
        children.append(
            {
                "id": id_match.group(1),
                "memory": memory_match.group(1),
                "changelog": changelog_match.group(1),
            }
        )
        index += 3
    return children, body


def update_root_index(root_memory: Path, subsystems: list[str]) -> bool:
    content = root_memory.read_text(encoding="utf-8")
    try:
        children, body = parse_root_memory(content)
    except ValueError as exc:
        if not content.startswith(FRONTMATTER_START):
            children, body = [], content
        else:
            raise ValueError(f"cannot update root MEMORY.md: {exc}") from exc
    indexed = [child["id"] for child in children]
    combined = indexed + [name for name in subsystems if name not in indexed]
    rendered = render_root_memory(combined, body)
    if rendered == content:
        return False
    root_memory.write_text(rendered, encoding="utf-8")
    return True


def init(entity_dir: Path, subsystems: list[str]) -> int:
    if not entity_dir.is_dir():
        print(f"ERROR: entity directory not found: {entity_dir}", file=sys.stderr)
        return 2
    for subsystem in subsystems:
        validate_subsystem(subsystem)
    created: list[Path] = []
    root_memory = entity_dir / "MEMORY.md"
    if ensure_file(root_memory, render_root_memory([], ROOT_MEMORY_BODY)):
        created.append(root_memory)
    if ensure_file(entity_dir / "CHANGELOG.md", ROOT_CHANGELOG):
        created.append(entity_dir / "CHANGELOG.md")
    memories = entity_dir / "memories"
    memories.mkdir(exist_ok=True)
    for subsystem in subsystems:
        directory = memories / subsystem
        directory.mkdir(exist_ok=True)
        memory_file = directory / "MEMORY.md"
        changelog_file = directory / "CHANGELOG.md"
        if ensure_file(memory_file, SUBSYSTEM_MEMORY.format(subsystem=subsystem)):
            created.append(memory_file)
        if ensure_file(changelog_file, SUBSYSTEM_CHANGELOG.format(subsystem=subsystem)):
            created.append(changelog_file)
    if update_root_index(root_memory, subsystems) and root_memory not in created:
        print("updated MEMORY.md")
    for path in created:
        print(f"created {path.relative_to(entity_dir)}")
    print(f"initialized directory context: subsystems={len(subsystems)}")
    return verify(entity_dir)


def verify(entity_dir: Path) -> int:
    errors: list[str] = []
    root_memory = entity_dir / "MEMORY.md"
    for required in ("MEMORY.md", "CHANGELOG.md"):
        if not (entity_dir / required).is_file():
            errors.append(f"missing root file: {required}")
    memories = entity_dir / "memories"
    if not memories.is_dir():
        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1
        print("verified flat directory context: root files OK")
        return 0

    children: list[dict[str, str]] = []
    if root_memory.is_file():
        try:
            children, _ = parse_root_memory(root_memory.read_text(encoding="utf-8"))
        except ValueError as exc:
            errors.append(str(exc))

    directories = sorted(path for path in memories.iterdir() if path.is_dir())
    actual = {directory.name for directory in directories}
    for directory in directories:
        try:
            validate_subsystem(directory.name)
        except ValueError as exc:
            errors.append(str(exc))
        for required in ("MEMORY.md", "CHANGELOG.md"):
            if not (directory / required).is_file():
                errors.append(f"missing subsystem file: memories/{directory.name}/{required}")

    seen: set[str] = set()
    indexed: set[str] = set()
    for child in children:
        subsystem = child["id"]
        if subsystem in seen:
            errors.append(f"duplicate root index entry: {subsystem}")
            continue
        seen.add(subsystem)
        try:
            validate_subsystem(subsystem)
        except ValueError as exc:
            errors.append(f"invalid root index entry: {exc}")
            continue
        expected_memory = f"memories/{subsystem}/MEMORY.md"
        expected_changelog = f"memories/{subsystem}/CHANGELOG.md"
        if child["memory"] != expected_memory:
            errors.append(f"incorrect root index memory path for {subsystem}: {child['memory']}")
        if child["changelog"] != expected_changelog:
            errors.append(f"incorrect root index changelog path for {subsystem}: {child['changelog']}")
        if subsystem not in actual:
            errors.append(f"root index references missing subsystem: {subsystem}")
        indexed.add(subsystem)

    for subsystem in sorted(actual - indexed):
        errors.append(f"subsystem missing from root index: {subsystem}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"verified directory context: root files OK, subsystems={len(directories)}")
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
