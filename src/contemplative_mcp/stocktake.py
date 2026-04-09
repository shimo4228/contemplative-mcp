"""Skills and rules quality audit."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from . import prompts
from .config import RULES_DIR, SKILLS_DIR
from .distill import _strip_code_fence
from .llm import generate

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MergeGroup:
    filenames: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class QualityIssue:
    filename: str
    issue: str


@dataclass(frozen=True)
class StocktakeResult:
    merge_groups: tuple[MergeGroup, ...]
    quality_issues: tuple[QualityIssue, ...]
    total_files: int


def _read_files(directory: Path) -> list[tuple[str, str]]:
    """Read *.md files, strip YAML frontmatter."""
    items: list[tuple[str, str]] = []
    if not directory.exists():
        return items
    for path in sorted(directory.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                text = parts[2].strip()
        items.append((path.name, text))
    return items


def _format_items(items: list[tuple[str, str]]) -> str:
    """Format files for LLM input."""
    parts = []
    for filename, body in items:
        parts.append(f"=== {filename} ===\n{body}")
    return "\n\n".join(parts)


def _find_duplicate_groups(
    items: list[tuple[str, str]], prompt_template: str
) -> list[MergeGroup]:
    """Use LLM to find semantically redundant groups."""
    if len(items) < 2:
        return []

    formatted = _format_items(items)
    prompt_text = prompt_template.format(items=formatted)
    raw = generate(prompt_text)
    if not raw:
        return []

    try:
        data = json.loads(_strip_code_fence(raw))
        groups = data.get("groups", [])
        return [
            MergeGroup(
                filenames=tuple(g["files"]),
                reason=g.get("reason", ""),
            )
            for g in groups
            if "files" in g and len(g["files"]) >= 2
        ]
    except (json.JSONDecodeError, KeyError, TypeError):
        return []


def _check_skill_quality(filename: str, body: str) -> QualityIssue | None:
    """Check skill structural quality."""
    if len(body) < 200:
        return QualityIssue(filename, "Content too short (<200 chars)")
    if "## Problem" not in body and "## Solution" not in body:
        return QualityIssue(filename, "Missing ## Problem or ## Solution section")
    return None


def _check_rule_quality(filename: str, body: str) -> QualityIssue | None:
    """Check rule structural quality."""
    if len(body) < 200:
        return QualityIssue(filename, "Content too short (<200 chars)")
    if "**When:**" not in body and "**Do:**" not in body:
        return QualityIssue(filename, "Missing **When:** or **Do:** clause")
    return None


def run_skill_stocktake(
    skills_dir: Path | None = None,
) -> StocktakeResult:
    """Audit skills for duplicates and quality issues."""
    sdir = skills_dir or SKILLS_DIR
    items = _read_files(sdir)

    groups = _find_duplicate_groups(items, prompts.get("stocktake_skills"))
    issues = [
        issue
        for filename, body in items
        if (issue := _check_skill_quality(filename, body)) is not None
    ]

    return StocktakeResult(
        merge_groups=tuple(groups),
        quality_issues=tuple(issues),
        total_files=len(items),
    )


def run_rules_stocktake(
    rules_dir: Path | None = None,
) -> StocktakeResult:
    """Audit rules for duplicates and quality issues."""
    rdir = rules_dir or RULES_DIR
    items = _read_files(rdir)

    groups = _find_duplicate_groups(items, prompts.get("stocktake_rules"))
    issues = [
        issue
        for filename, body in items
        if (issue := _check_rule_quality(filename, body)) is not None
    ]

    return StocktakeResult(
        merge_groups=tuple(groups),
        quality_issues=tuple(issues),
        total_files=len(items),
    )


def format_report(result: StocktakeResult, label: str) -> str:
    """Format StocktakeResult as human-readable report."""
    lines = [f"# {label} Stocktake Report", f"Total files: {result.total_files}", ""]

    if result.merge_groups:
        lines.append("## Duplicate Groups")
        for i, group in enumerate(result.merge_groups, 1):
            lines.append(f"\n### Group {i}")
            lines.append(f"Reason: {group.reason}")
            for f in group.filenames:
                lines.append(f"  - {f}")
    else:
        lines.append("No duplicates found.")

    lines.append("")

    if result.quality_issues:
        lines.append("## Quality Issues")
        for issue in result.quality_issues:
            lines.append(f"- **{issue.filename}**: {issue.issue}")
    else:
        lines.append("No quality issues found.")

    return "\n".join(lines)
