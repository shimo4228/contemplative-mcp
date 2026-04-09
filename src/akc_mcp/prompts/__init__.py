"""Prompt templates for distillation pipeline."""

from __future__ import annotations

from pathlib import Path

_DIR = Path(__file__).parent


def _load(name: str) -> str:
    return (_DIR / f"{name}.md").read_text(encoding="utf-8")


# Lazy-loaded prompt cache
_cache: dict[str, str] = {}


def get(name: str) -> str:
    """Load a prompt template by name (cached)."""
    if name not in _cache:
        _cache[name] = _load(name)
    return _cache[name]
