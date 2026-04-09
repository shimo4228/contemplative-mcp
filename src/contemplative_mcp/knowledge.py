"""KnowledgeStore — JSON-persisted learned patterns with time-decay importance."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import KNOWLEDGE_PATH, validate_content, write_restricted

logger = logging.getLogger(__name__)


def effective_importance(pattern: dict[str, Any]) -> float:
    """Compute importance with time decay: base * 0.95^days_elapsed."""
    base = pattern.get("importance", 0.5)
    distilled = pattern.get("distilled", "unknown")
    if distilled == "unknown":
        return max(0.0, min(1.0, base * 0.1))
    try:
        dt = datetime.fromisoformat(distilled)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        days = (datetime.now(timezone.utc) - dt).total_seconds() / 86400
        return max(0.0, min(1.0, base * (0.95 ** days)))
    except (ValueError, TypeError):
        return max(0.0, min(1.0, base * 0.1))


class KnowledgeStore:
    """Manages JSON-persisted learned patterns."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or KNOWLEDGE_PATH
        self._patterns: list[dict[str, Any]] = []
        if self._path.exists():
            self.load()

    def load(self) -> None:
        """Load patterns from JSON file."""
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                self._patterns = [
                    p for p in data
                    if isinstance(p, dict) and validate_content(p.get("pattern", ""))
                ]
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load knowledge: %s", e)
            self._patterns = []

    def save(self) -> None:
        """Persist patterns to JSON with atomic write."""
        content = json.dumps(self._patterns, ensure_ascii=False, indent=2)
        write_restricted(self._path, content)

    def add_learned_pattern(
        self,
        pattern: str,
        distilled: str | None = None,
        source: str | None = None,
        importance: float = 0.5,
        category: str = "uncategorized",
    ) -> None:
        """Append a pattern to the store."""
        entry: dict[str, Any] = {
            "pattern": pattern,
            "distilled": distilled or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M"),
            "importance": importance,
            "category": category,
        }
        if source:
            entry["source"] = source
        self._patterns.append(entry)

    def get_raw_patterns(self) -> list[dict[str, Any]]:
        """Return all pattern dicts (copy)."""
        return list(self._patterns)

    def get_learned_patterns(self, category: str | None = None) -> list[str]:
        """Return pattern text only, optionally filtered by category."""
        return [
            p["pattern"] for p in self._patterns
            if (category is None or p.get("category") == category)
            and "pattern" in p
        ]

    def get_learned_patterns_since(
        self, since: str, category: str | None = None
    ) -> list[str]:
        """Return patterns distilled after ISO timestamp."""
        return [
            p["pattern"] for p in self._patterns
            if p.get("distilled", "") >= since
            and (category is None or p.get("category") == category)
            and "pattern" in p
        ]

    def get_context_string(
        self, limit: int = 50, category: str | None = None
    ) -> str:
        """Return top-N patterns by effective importance as bullet list."""
        filtered = [
            p for p in self._patterns
            if category is None or p.get("category") == category
        ]
        ranked = sorted(filtered, key=effective_importance, reverse=True)[:limit]
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")
        for p in ranked:
            p["last_accessed"] = now
        return "\n".join(f"- {p['pattern']}" for p in ranked)

    @property
    def pattern_count(self) -> int:
        return len(self._patterns)
