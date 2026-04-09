"""Rule distillation from behavioral skills."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from . import prompts
from .config import MAX_SLUG_LENGTH, MIN_SKILLS_REQUIRED, validate_content
from .llm import generate


@dataclass(frozen=True)
class RuleResult:
    text: str
    filename: str
    target_path: Path


@dataclass(frozen=True)
class RulesDistillResult:
    rules: tuple[RuleResult, ...]
    dropped_count: int
    rules_dir: Path


def _read_skills(skills_dir: Path) -> list[str]:
    """Read skill file bodies from directory."""
    skills: list[str] = []
    if not skills_dir.exists():
        return skills
    for path in sorted(skills_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        # Strip YAML frontmatter
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                text = parts[2].strip()
        skills.append(text)
    return skills


def _split_rules(text: str) -> list[str]:
    """Split multi-rule document on ## Rule boundaries."""
    parts = re.split(r"(?=^## Rule)", text, flags=re.MULTILINE)
    return [p.strip() for p in parts if p.strip()]


def _extract_title(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("# ") or line.startswith("## Rule"):
            title = re.sub(r"^#+\s*(Rule\s*\d*:?\s*)?", "", line)
            return title.strip()
    return None


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug[:MAX_SLUG_LENGTH]


def distill_rules(
    skills_dir: Path | None = None,
    rules_dir: Path | None = None,
    full: bool = False,
) -> str | RulesDistillResult:
    """Distill universal rules from behavioral skills.

    Two-stage pipeline: free-form extraction -> structured Markdown.
    Returns RulesDistillResult (does not write files).
    skills_dir and rules_dir should be provided by the caller
    for multi-tenant safety.
    """
    if skills_dir is None or rules_dir is None:
        raise ValueError("skills_dir and rules_dir are required")
    sdir = skills_dir
    rdir = rules_dir

    skill_texts = _read_skills(sdir)
    if len(skill_texts) < MIN_SKILLS_REQUIRED:
        return f"Not enough skills ({len(skill_texts)}/{MIN_SKILLS_REQUIRED})."

    # Stage 1: Free-form extraction
    prompt_text = prompts.get("rules_distill").format(
        patterns="\n\n---\n\n".join(skill_texts)
    )
    raw = generate(prompt_text)
    if not raw:
        return "LLM failed to extract rules."

    # Stage 2: Refine to structured Markdown
    refine_prompt = prompts.get("rules_distill_refine").format(raw_output=raw)
    refined = generate(refine_prompt)
    if not refined:
        return "LLM failed to refine rules."

    # Split into individual rules
    rule_sections = _split_rules(refined)
    rules: list[RuleResult] = []
    dropped = 0

    for section in rule_sections:
        title = _extract_title(section)
        if not title:
            dropped += 1
            continue

        if not validate_content(section):
            dropped += 1
            continue

        slug = _slugify(title)
        if not slug:
            dropped += 1
            continue

        filename = f"{slug}-{date.today().strftime('%Y%m%d')}.md"
        target = rdir / filename

        if not target.resolve().is_relative_to(rdir.resolve()):
            dropped += 1
            continue

        rules.append(RuleResult(text=section, filename=filename, target_path=target))

    return RulesDistillResult(
        rules=tuple(rules),
        dropped_count=dropped,
        rules_dir=rdir,
    )
