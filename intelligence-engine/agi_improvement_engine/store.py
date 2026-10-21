"""Append-only session and learning-event records with secret scrubbing."""

from __future__ import annotations

import json
import re
from pathlib import Path
from threading import Lock
from typing import Any

_LOCK = Lock()
_SECRET = re.compile(r"(?i)(api[_-]?key|authorization|cookie|token|secret)")


def scrub(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): ("[REDACTED]" if _SECRET.search(str(k)) else scrub(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [scrub(v) for v in value]
    return value


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(scrub(record), ensure_ascii=False, default=str) + "\n"
    with _LOCK, path.open("a", encoding="utf-8") as handle:
        handle.write(line)
