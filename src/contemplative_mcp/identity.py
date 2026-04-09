"""Identity management — read/write identity.md with validation."""

from __future__ import annotations

from pathlib import Path

from .config import IDENTITY_PATH, validate_content, write_restricted


def read_identity(path: Path | None = None) -> str:
    """Read identity.md content."""
    p = path or IDENTITY_PATH
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8")


def write_identity(content: str, path: Path | None = None) -> bool:
    """Write identity.md with validation. Returns True on success."""
    if not validate_content(content):
        return False
    p = path or IDENTITY_PATH
    write_restricted(p, content)
    return True
