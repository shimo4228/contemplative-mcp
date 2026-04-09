"""Anthropic API backend for LLM calls."""

from __future__ import annotations

import hashlib
import logging
from collections import OrderedDict
from contextvars import ContextVar
from typing import Any

import anthropic

from .config import validate_content

logger = logging.getLogger(__name__)

_client: anthropic.Anthropic | None = None
_model: str = "claude-sonnet-4-6"

# Per-request API key override for multi-tenant mode.
_override_api_key: ContextVar[str] = ContextVar("override_api_key", default="")
_CLIENT_CACHE_MAX = 128
_client_cache: OrderedDict[str, anthropic.Anthropic] = OrderedDict()


def set_request_key(key: str) -> None:
    """Set the per-request API key override (call from middleware)."""
    _override_api_key.set(key)


def get_request_key() -> str:
    """Get the current per-request API key override."""
    return _override_api_key.get("")


def configure(
    *,
    api_key: str | None = None,
    model: str | None = None,
) -> None:
    """Configure the Anthropic client. Falls back to ANTHROPIC_API_KEY env var."""
    global _client, _model
    _client = anthropic.Anthropic(api_key=api_key)
    if model:
        _model = model


def generate(
    prompt: str,
    system: str | None = None,
    max_tokens: int = 4096,
    format: dict[str, Any] | None = None,
) -> str | None:
    """Generate text using Anthropic API.

    Returns sanitized text or None on failure.
    """
    global _client
    if _client is None:
        configure()
    assert _client is not None

    # Use per-request API key if set (multi-tenant mode)
    override_key = _override_api_key.get("")
    if override_key:
        cache_key = hashlib.sha256(override_key.encode()).hexdigest()
        if cache_key not in _client_cache:
            if len(_client_cache) >= _CLIENT_CACHE_MAX:
                _client_cache.popitem(last=False)
            _client_cache[cache_key] = anthropic.Anthropic(api_key=override_key)
        client = _client_cache[cache_key]
    else:
        client = _client

    try:
        kwargs: dict[str, Any] = {
            "model": _model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        if format:
            # Anthropic supports JSON mode via tool_choice
            kwargs["messages"][0]["content"] = (
                f"{prompt}\n\nRespond with ONLY valid JSON, no explanation."
            )

        msg = client.messages.create(**kwargs)
        text = msg.content[0].text if msg.content else None

        if text and not validate_content(text):
            logger.warning("LLM output contained forbidden patterns, sanitizing")
            return _sanitize(text)

        return text

    except Exception as e:
        logger.error("LLM error: %s", e)
        return None


def _sanitize(text: str) -> str:
    """Remove lines containing forbidden patterns."""
    from .config import FORBIDDEN_SUBSTRING_PATTERNS, FORBIDDEN_WORD_PATTERNS

    lines = text.splitlines()
    clean = []
    for line in lines:
        lower = line.lower()
        skip = False
        for pattern in FORBIDDEN_SUBSTRING_PATTERNS:
            if pattern in lower:
                skip = True
                break
        if not skip:
            for regex in FORBIDDEN_WORD_PATTERNS:
                if regex.search(line):
                    skip = True
                    break
        if not skip:
            clean.append(line)
    return "\n".join(clean)


def reset() -> None:
    """Reset client state (for testing)."""
    global _client, _model
    _client = None
    _model = "claude-sonnet-4-6"
