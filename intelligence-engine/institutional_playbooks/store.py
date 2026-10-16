"""In-memory IAP selection telemetry store."""

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
        "iap_version": row.get("iap_version"),
        "playbook_id": row.get("playbook_id"),
        "category": row.get("category"),
        "sector": row.get("sector"),
        "intent_v2": row.get("intent_v2"),
        "playbook_ids": row.get("playbook_ids") or [],
        "checklist_steps": ((row.get("checklist") or {}).get("n_steps")),
        "procedure_steps": ((row.get("procedure") or {}).get("n_steps")),
        "confidence": (row.get("confidence") or {}).get("band"),
        "confidence_pct": (row.get("confidence") or {}).get("pct"),
        "validation_passed": (row.get("validation") or {}).get("passed"),
        "as_of": row.get("as_of"),
        "guides_reasoning": True,
    }
    _SELECTIONS.append(slim)
    if len(_SELECTIONS) > _MAX:
        del _SELECTIONS[: len(_SELECTIONS) - _MAX]


def list_selections(*, limit: int = 100) -> list[dict[str, Any]]:
    return list(reversed(_SELECTIONS[-limit:]))


def clear() -> None:
    _SELECTIONS.clear()
