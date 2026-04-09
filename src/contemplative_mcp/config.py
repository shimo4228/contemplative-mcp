"""Path resolution and security constants."""

from __future__ import annotations

import os
import re
from pathlib import Path

# --- Data directory ---
CONTEMPLATIVE_HOME = Path(
    os.environ.get(
        "CONTEMPLATIVE_HOME", str(Path.home() / ".config" / "contemplative")
    )
)

# Note: Per-user paths are resolved at request time in server.py.
# Global path constants were removed for multi-tenant safety.

# --- File permissions ---
RESTRICTED_MODE = 0o600
DIR_MODE = 0o700

# --- Security: forbidden patterns ---
FORBIDDEN_SUBSTRING_PATTERNS: tuple[str, ...] = (
    "api_key",
    "api-key",
    "apikey",
    "secret_key",
    "secret-key",
    "access_token",
    "access-token",
    "bearer ",
    "authorization:",
    "password:",
    "credentials",
    "begin rsa private key",
    "begin openssh private key",
)

FORBIDDEN_WORD_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bsk-[a-zA-Z0-9]{20,}\b"),  # API key patterns
    re.compile(r"\bghp_[a-zA-Z0-9]{36}\b"),  # GitHub tokens
    re.compile(r"\bxoxb-[a-zA-Z0-9-]+\b"),  # Slack tokens
)

# --- Distillation constants ---
BATCH_SIZE = 30
MIN_PATTERNS_REQUIRED = 3
MIN_SKILLS_REQUIRED = 3
MAX_SLUG_LENGTH = 50
DEDUP_IMPORTANCE_FLOOR = 0.05


def validate_content(text: str) -> bool:
    """Check text for forbidden patterns. Returns True if clean."""
    lower = text.lower()
    for pattern in FORBIDDEN_SUBSTRING_PATTERNS:
        if pattern in lower:
            return False
    for regex in FORBIDDEN_WORD_PATTERNS:
        if regex.search(text):
            return False
    return True


def safe_path(base_dir: Path, filename: str) -> Path | None:
    """Resolve filename under base_dir, rejecting path traversal."""
    resolved = (base_dir / filename).resolve()
    if not resolved.is_relative_to(base_dir.resolve()):
        return None
    return resolved


def write_restricted(path: Path, content: str) -> None:
    """Write content to file with restricted permissions (0600)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.chmod(RESTRICTED_MODE)
    tmp.replace(path)
