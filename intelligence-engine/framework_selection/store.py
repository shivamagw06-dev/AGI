"""In-memory IFSE selection telemetry store."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

_SELECTIONS: list[dict[str, Any]] = []
_MAX = 500


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def record_selection(row: dict[str, Any]) -> None:
    slim = {
        "recorded_at": utc_now(),
        "ifse_version": row.get("ifse_version"),
        "sector": row.get("sector"),
        "intent_v2": row.get("intent_v2"),
        "framework_ids": row.get("framework_ids") or [],
        "multi_framework": row.get("multi_framework"),
        "confidence": (row.get("confidence") or {}).get("band"),
        "confidence_pct": (row.get("confidence") or {}).get("pct"),
        "validation_passed": (row.get("validation") or {}).get("passed"),
        "failures": (row.get("validation") or {}).get("failures") or [],
        "forbidden_rejected": row.get("forbidden_rejected") or [],
        "as_of": row.get("as_of"),
    }
    _SELECTIONS.append(slim)
    if len(_SELECTIONS) > _MAX:
        del _SELECTIONS[: len(_SELECTIONS) - _MAX]


def list_selections(*, limit: int = 100) -> list[dict[str, Any]]:
    return list(reversed(_SELECTIONS[-limit:]))


def clear() -> None:
    _SELECTIONS.clear()
