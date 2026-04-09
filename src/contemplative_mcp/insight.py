"""Skill extraction from learned patterns."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from . import prompts
from .config import BATCH_SIZE, MAX_SLUG_LENGTH, MIN_PATTERNS_REQUIRED, SKILLS_DIR, validate_content
from .knowledge import KnowledgeStore
from .llm import generate


@dataclass(frozen=True)
class SkillResult:
    text: str
    filename: str
    target_path: Path


@dataclass(frozen=True)
class InsightResult:
    skills: tuple[SkillResult, ...]
    dropped_count: int
    skills_dir: Path


def _extract_title(text: str) -> str | None:
    """Extract title from # heading."""
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def _slugify(title: str) -> str:
    """Convert title to filesystem-safe slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower())
    slug = slug.strip("-")
    return slug[:MAX_SLUG_LENGTH]


def extract_insight(
    knowledge_store: KnowledgeStore | None = None,
    skills_dir: Path | None = None,
    full: bool = False,
) -> str | InsightResult:
    """Extract behavioral skills from learned patterns.

    Returns InsightResult (does not write files).
    """
    knowledge = knowledge_store or KnowledgeStore()
    sdir = skills_dir or SKILLS_DIR

    patterns = knowledge.get_learned_patterns(category="uncategorized")
    if len(patterns) < MIN_PATTERNS_REQUIRED:
        return f"Not enough patterns ({len(patterns)}/{MIN_PATTERNS_REQUIRED})."

    skills: list[SkillResult] = []
    dropped = 0

    for i in range(0, len(patterns), BATCH_SIZE):
        batch = patterns[i : i + BATCH_SIZE]
        prompt_text = prompts.get("insight_extraction").format(
            patterns="\n".join(f"- {p}" for p in batch),
            insights="(none)",
        )
        raw = generate(prompt_text)
        if not raw:
            dropped += 1
            continue

        title = _extract_title(raw)
        if not title:
            dropped += 1
            continue

        if not validate_content(raw):
            dropped += 1
            continue

        slug = _slugify(title)
        if not slug:
            dropped += 1
            continue

        filename = f"{slug}-{date.today().strftime('%Y%m%d')}.md"
        target = sdir / filename

        # Path traversal check
        if not target.resolve().is_relative_to(sdir.resolve()):
            dropped += 1
            continue

        skills.append(SkillResult(text=raw, filename=filename, target_path=target))

    return InsightResult(
        skills=tuple(skills),
        dropped_count=dropped,
        skills_dir=sdir,
    )
