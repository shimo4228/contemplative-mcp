"""Identity management — read/write identity.md with validation."""

from __future__ import annotations

from pathlib import Path

from .config import validate_content, write_restricted


def read_identity(path: Path) -> str:
    """Read identity.md content."""
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def write_identity(content: str, path: Path) -> bool:
    """Write identity.md with validation. Returns True on success."""
    if not validate_content(content):
        return False
    write_restricted(path, content)
    return True
