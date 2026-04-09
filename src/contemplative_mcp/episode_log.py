"""EpisodeLog — append-only daily JSONL episode storage."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


class EpisodeLog:
    """Append-only daily JSONL logs."""

    def __init__(self, log_dir: Path | None = None) -> None:
        if log_dir is None:
            raise ValueError("log_dir is required")
        self._log_dir = log_dir

    def append(self, record_type: str, data: dict[str, Any]) -> None:
        """Append a record to today's JSONL file."""
        self._log_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc)
        record = {
            "ts": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "type": record_type,
            "data": data,
        }
        path = self._log_dir / f"{now.strftime('%Y-%m-%d')}.jsonl"
        old_umask = None
        try:
            import os
            old_umask = os.umask(0o177)
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        finally:
            if old_umask is not None:
                import os
                os.umask(old_umask)

    def read_range(
        self, days: int = 1, record_type: str | None = None
    ) -> list[dict[str, Any]]:
        """Read records from past N days."""
        records: list[dict[str, Any]] = []
        now = datetime.now(timezone.utc)
        for i in range(days):
            date = now - timedelta(days=i)
            path = self._log_dir / f"{date.strftime('%Y-%m-%d')}.jsonl"
            if path.exists():
                records.extend(self._read_file(path))
        if record_type:
            records = [r for r in records if r.get("type") == record_type]
        records.sort(key=lambda r: r.get("ts", ""))
        return records

    @staticmethod
    def _read_file(path: Path) -> list[dict[str, Any]]:
        """Read all records from a single JSONL file."""
        records: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning("Skipping malformed line in %s", path)
        return records
