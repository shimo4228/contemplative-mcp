"""Sleep-time memory distillation — episodes to learned patterns."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import prompts
from .config import BATCH_SIZE, validate_content
from .episode_log import EpisodeLog
from .knowledge import KnowledgeStore
from .llm import generate

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IdentityResult:
    text: str
    target_path: Path


def summarize_record(record_type: str, data: dict[str, Any]) -> str:
    """One-line summary of an episode record."""
    if record_type == "interaction":
        direction = data.get("direction", "?")
        agent = data.get("agent_name", "unknown")
        summary = data.get("content_summary", "")
        return f"[{direction}] {agent}: {summary}"
    elif record_type == "post":
        title = data.get("title", "untitled")
        topic = data.get("topic_summary", "")
        return f"[post] {title} — {topic}"
    elif record_type == "insight":
        return f"[insight] {data.get('observation', '')}"
    else:
        return f"[{record_type}] {json.dumps(data, ensure_ascii=False)[:200]}"


def _strip_code_fence(text: str) -> str:
    """Remove markdown code fences from LLM output."""
    lines = text.strip().splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _classify_episode(
    episode_summary: str, constitution: str
) -> str:
    """Classify a single episode as constitutional/noise/uncategorized."""
    prompt_text = prompts.get("distill_classify").format(
        constitution=constitution, episode=episode_summary
    )
    result = generate(prompt_text)
    if not result:
        return "uncategorized"
    word = result.strip().lower().split()[0] if result.strip() else "uncategorized"
    if word in ("constitutional", "noise", "uncategorized"):
        return word
    return "uncategorized"


def _extract_patterns(episodes: list[str], category: str) -> list[str]:
    """Extract patterns from a batch of episode summaries."""
    template_name = "distill_constitutional" if category == "constitutional" else "distill"
    prompt_text = prompts.get(template_name).format(
        episodes="\n".join(episodes)
    )
    raw = generate(prompt_text)
    if not raw:
        return []

    # Refine into structured patterns
    refine_prompt = prompts.get("distill_refine").format(raw_output=raw)
    refined = generate(refine_prompt)
    if not refined:
        return [raw]

    try:
        data = json.loads(_strip_code_fence(refined))
        patterns = data.get("patterns", [])
        return [p for p in patterns if isinstance(p, str) and p.strip()]
    except (json.JSONDecodeError, AttributeError):
        return [refined]


def _score_importance(patterns: list[str]) -> list[float]:
    """Rate pattern importance via LLM."""
    prompt_text = prompts.get("distill_importance").format(
        patterns="\n".join(f"{i+1}. {p}" for i, p in enumerate(patterns))
    )
    raw = generate(prompt_text)
    if not raw:
        return [0.5] * len(patterns)
    try:
        data = json.loads(_strip_code_fence(raw))
        scores = data.get("scores", [])
        return [max(0.0, min(1.0, s / 10.0)) for s in scores]
    except (json.JSONDecodeError, AttributeError):
        return [0.5] * len(patterns)


def _dedup_patterns(
    new_patterns: list[str],
    new_importances: list[float],
    existing_patterns: list[str],
) -> tuple[list[str], list[float], int, int]:
    """Deduplicate new patterns against existing ones.

    Returns (add_patterns, add_importances, skip_count, update_count).
    """
    if not existing_patterns:
        return new_patterns, new_importances, 0, 0

    # Build dedup prompt
    items = []
    for i, p in enumerate(new_patterns):
        items.append(f"NEW {i+1}: {p}")
    for i, p in enumerate(existing_patterns):
        items.append(f"EXISTING {i+1}: {p}")

    prompt_text = prompts.get("distill_dedup").format(
        dedup_items="\n".join(items)
    )
    raw = generate(prompt_text)
    if not raw:
        return new_patterns, new_importances, 0, 0

    try:
        data = json.loads(_strip_code_fence(raw))
        decisions = data.get("decisions", [])
    except (json.JSONDecodeError, AttributeError):
        return new_patterns, new_importances, 0, 0

    add_patterns: list[str] = []
    add_importances: list[float] = []
    skip_count = 0
    update_count = 0

    for i, decision in enumerate(decisions):
        if i >= len(new_patterns):
            break
        d = decision.strip().upper()
        if d == "ADD":
            add_patterns.append(new_patterns[i])
            add_importances.append(new_importances[i])
        elif d == "SKIP":
            skip_count += 1
        elif d.startswith("UPDATE"):
            update_count += 1
        else:
            add_patterns.append(new_patterns[i])
            add_importances.append(new_importances[i])

    return add_patterns, add_importances, skip_count, update_count


def distill(
    days: int = 1,
    dry_run: bool = False,
    episode_log: EpisodeLog | None = None,
    knowledge_store: KnowledgeStore | None = None,
    constitution: str = "",
) -> str:
    """Distill recent episodes into learned patterns.

    Returns summary string. If dry_run, does not persist.
    episode_log and knowledge_store should be provided by the caller
    for multi-tenant safety.
    """
    if episode_log is None or knowledge_store is None:
        raise ValueError("episode_log and knowledge_store are required")
    log = episode_log
    knowledge = knowledge_store

    records = log.read_range(days=days)
    if not records:
        return "No episodes found for the specified period."

    # Summarize records
    summaries = [
        summarize_record(r.get("type", ""), r.get("data", {}))
        for r in records
    ]

    # Classify episodes
    classified: dict[str, list[str]] = {
        "constitutional": [],
        "uncategorized": [],
    }
    for summary in summaries:
        category = _classify_episode(summary, constitution)
        if category in classified:
            classified[category].append(summary)

    # Extract patterns per category
    all_new_patterns: list[str] = []
    all_importances: list[float] = []
    total_extracted = 0

    for category, cat_summaries in classified.items():
        if not cat_summaries:
            continue

        # Process in batches
        for i in range(0, len(cat_summaries), BATCH_SIZE):
            batch = cat_summaries[i : i + BATCH_SIZE]
            patterns = _extract_patterns(batch, category)
            if not patterns:
                continue

            importances = _score_importance(patterns)
            # Pad if lengths mismatch
            while len(importances) < len(patterns):
                importances.append(0.5)

            # Dedup against existing
            existing = knowledge.get_learned_patterns(category=category)
            add_p, add_i, skipped, updated = _dedup_patterns(
                patterns, importances, existing
            )

            for pattern, importance in zip(add_p, add_i):
                all_new_patterns.append(pattern)
                all_importances.append(importance)
                if not dry_run:
                    knowledge.add_learned_pattern(
                        pattern=pattern,
                        importance=importance,
                        category=category,
                        source=f"distill-{days}d",
                    )
                total_extracted += 1

    if not dry_run and total_extracted > 0:
        knowledge.save()

    prefix = "[DRY RUN] " if dry_run else ""
    return (
        f"{prefix}Distilled {total_extracted} patterns from "
        f"{len(records)} episodes ({days} day(s)).\n"
        + "\n".join(f"- {p}" for p in all_new_patterns)
    )


def distill_identity(
    knowledge_store: KnowledgeStore | None = None,
    identity_path: Path | None = None,
) -> str | IdentityResult:
    """Generate updated identity from accumulated knowledge.

    Returns IdentityResult with proposed text (does not write).
    knowledge_store and identity_path should be provided by the caller
    for multi-tenant safety.
    """
    if knowledge_store is None or identity_path is None:
        raise ValueError("knowledge_store and identity_path are required")
    knowledge = knowledge_store
    path = identity_path

    context = knowledge.get_context_string(limit=50)
    if not context:
        return "Not enough patterns to distill identity."

    current = ""
    if path.exists():
        current = path.read_text(encoding="utf-8")

    prompt_text = prompts.get("identity_distill").format(
        current_identity=current or "(no current identity)",
        knowledge=context,
    )
    raw = generate(prompt_text)
    if not raw:
        return "LLM failed to generate identity update."

    # Refine
    refine_prompt = prompts.get("identity_refine").format(raw_output=raw)
    refined = generate(refine_prompt)
    text = refined or raw

    if not validate_content(text):
        return "Generated identity contained forbidden patterns."

    return IdentityResult(text=text, target_path=path)
