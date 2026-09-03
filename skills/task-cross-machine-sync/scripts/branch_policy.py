#!/usr/bin/env python3
"""Resolve and validate repository-specific branch promotion paths.

Policy discovery is deliberately opt-in: repositories may declare a JSON
configuration or a short Markdown policy. Repositories without one use the
portable default (feat -> develop -> main).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_PATH = ("feat", "develop", "main")
_CONFIG_NAMES = (
    ".branch-promotion.json",
    "branch-promotion.json",
    "repository-policy.json",
    ".hermes/branch-policy.json",
    ".github/branch-policy.json",
)
_DOC_NAMES = (
    "BRANCHING.md",
    "branching.md",
    "CONTRIBUTING.md",
    "contributing.md",
    "DEVELOPMENT.md",
    "development.md",
    "docs/BRANCHING.md",
    "docs/branching.md",
    "docs/CONTRIBUTING.md",
    "docs/contributing.md",
    "docs/branch-policy.md",
    ".github/BRANCHING.md",
    ".github/branching.md",
)
_ARROW = re.compile(r"(?P<path>\b(?:feat|feature|develop|integration|main|master)(?:\s*(?:->|→)\s*(?:feat|feature|develop|integration|main|master))+\b)", re.I)


@dataclass(frozen=True)
class PromotionPolicy:
    path: tuple[str, ...]
    source: str
    explicit: bool

    def next_targets(self, source_branch: str) -> tuple[str, ...]:
        """Return only the next configured target for a source branch."""
        source = classify_branch(source_branch)
        aliases = (source, "feature" if source == "feat" else "feat" if source == "feature" else source)
        for alias in aliases:
            try:
                index = self.path.index(alias)
            except ValueError:
                continue
            return self.path[index + 1 : index + 2]
        return ()


def classify_branch(branch: str) -> str:
    """Map a concrete branch name to a policy role without changing it."""
    lowered = branch.strip().lower()
    if lowered.startswith("feat/"):
        return "feat"
    if lowered.startswith("feature/"):
        return "feature"
    return lowered


def _valid_path(value: Any) -> tuple[str, ...] | None:
    if isinstance(value, str):
        parts = re.split(r"\s*(?:->|→|,)\s*", value.strip())
    elif isinstance(value, list):
        parts = value
    else:
        return None
    normalized = tuple(str(item).strip().lower() for item in parts if str(item).strip())
    if len(normalized) >= 2 and all(re.fullmatch(r"[a-z][a-z0-9_-]*", item) for item in normalized):
        return normalized
    return None


def _config_path(data: dict[str, Any]) -> tuple[str, ...] | None:
    for key in ("promotion_path", "branch_promotion", "branch_promotion_path"):
        path = _valid_path(data.get(key))
        if path:
            return path
        nested = data.get(key)
        if isinstance(nested, dict):
            path = _valid_path(nested.get("path"))
            if path:
                return path
    return None


def _read_config(root: Path) -> PromotionPolicy | None:
    for relative in _CONFIG_NAMES:
        candidate = root / relative
        if not candidate.is_file():
            continue
        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid branch policy config {candidate}: {exc}") from exc
        path = _config_path(data) if isinstance(data, dict) else None
        if not path:
            raise ValueError(f"branch policy config has no valid promotion path: {candidate}")
        return PromotionPolicy(path, str(candidate), True)
    return None


def _read_docs(root: Path) -> PromotionPolicy | None:
    for relative in _DOC_NAMES:
        candidate = root / relative
        if not candidate.is_file():
            continue
        text = re.sub(r"[`*_]", "", candidate.read_text(encoding="utf-8"))
        match = _ARROW.search(text)
        if match:
            path = _valid_path(match.group("path"))
            if path:
                return PromotionPolicy(path, str(candidate), True)
    return None


def discover_policy(root: str | Path) -> PromotionPolicy:
    """Discover repository policy; use the safe generic default when absent."""
    repository = Path(root).expanduser().resolve()
    return _read_config(repository) or _read_docs(repository) or PromotionPolicy(DEFAULT_PATH, "default", False)


def validate_promotion(policy: PromotionPolicy, source_branch: str, target_branch: str) -> None:
    """Reject promotions that skip a repository's configured path."""
    source = classify_branch(source_branch)
    target = classify_branch(target_branch)
    expected = policy.next_targets(source)
    if not expected or target != expected[0]:
        expected_text = expected[0] if expected else "no configured target"
        raise ValueError(f"promotion {source_branch} -> {target_branch} violates {policy.source}; expected {expected_text}")


def promotion_steps(source_branch: str, target_branch: str, remote: str = "origin") -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return separate, non-force Git steps for a validated promotion."""
    return (
        ("git", "merge", "--ff-only", source_branch),
        ("git", "push", remote, f"HEAD:{target_branch}"),
    )
