"""In-process IMAI retrieval audit store."""

from __future__ import annotations

from copy import deepcopy
from threading import Lock
from typing import Any
from uuid import uuid4

_LOCK = Lock()
_RECORDS: list[dict[str, Any]] = []
_MAX = 500


def record(pack: dict[str, Any]) -> dict[str, Any]:
    row = {
        "record_id": f"imai-{uuid4().hex[:12]}",
        "module": pack.get("module"),
        "version": pack.get("version"),
        "status": pack.get("status"),
        "question": pack.get("question"),
        "as_of": pack.get("as_of"),
        "top_memory_ids": list(pack.get("top_memory_ids") or []),
        "have_we_seen_this_before": bool(pack.get("have_we_seen_this_before")),
        "quality_status": (pack.get("quality") or {}).get("status"),
        "scored_count": pack.get("scored_count"),
        "regimes": list(pack.get("regimes") or []),
    }
    with _LOCK:
        _RECORDS.append(row)
        if len(_RECORDS) > _MAX:
            del _RECORDS[: len(_RECORDS) - _MAX]
    return deepcopy(row)


def list_records(*, limit: int = 50) -> list[dict[str, Any]]:
    with _LOCK:
        rows = list(_RECORDS)
    return deepcopy(list(reversed(rows[-max(1, min(int(limit), 200)) :])))


def clear() -> None:
    with _LOCK:
        _RECORDS.clear()
