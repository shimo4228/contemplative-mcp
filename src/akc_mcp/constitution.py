"""Constitution management and amendment generation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import prompts
from .config import MIN_PATTERNS_REQUIRED, validate_content
from .knowledge import KnowledgeStore
from .llm import generate


@dataclass(frozen=True)
class AmendmentResult:
    text: str
    target_path: Path


def load_constitution(constitution_dir: Path | None = None) -> str:
    """Load constitution text from the first .md file in directory."""
    if constitution_dir is None:
        raise ValueError("constitution_dir is required")
    cdir = constitution_dir
    if not cdir.exists():
        return ""
    md_files = sorted(cdir.glob("*.md"))
    if not md_files:
        return ""
    return md_files[0].read_text(encoding="utf-8")


def amend_constitution(
    knowledge_store: KnowledgeStore | None = None,
    constitution_dir: Path | None = None,
) -> str | AmendmentResult:
    """Generate constitutional amendment from accumulated patterns.

    Returns AmendmentResult with proposed text (does not write).
    """
    if knowledge_store is None or constitution_dir is None:
        raise ValueError("knowledge_store and constitution_dir are required")
    knowledge = knowledge_store
    cdir = constitution_dir

    constitutional_patterns = knowledge.get_learned_patterns(category="constitutional")
    if len(constitutional_patterns) < MIN_PATTERNS_REQUIRED:
        return f"Not enough constitutional patterns ({len(constitutional_patterns)}/{MIN_PATTERNS_REQUIRED})."

    current = load_constitution(cdir)
    if not current:
        return "No current constitution found."

    context = knowledge.get_context_string(category="constitutional")
    prompt_text = prompts.get("constitution_amend").format(
        constitutional_patterns=context,
        current_constitution=current,
    )
    result = generate(prompt_text)
    if not result:
        return "LLM failed to generate amendment."

    if not validate_content(result):
        return "Generated amendment contained forbidden patterns."

    # Find target file
    md_files = sorted(cdir.glob("*.md"))
    target = md_files[0] if md_files else cdir / "constitution.md"

    return AmendmentResult(text=result, target_path=target)
