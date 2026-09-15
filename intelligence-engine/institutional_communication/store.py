"""ICE telemetry store."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

_ROWS: list[dict[str, Any]] = []
_MAX = 500


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def record(row: dict[str, Any]) -> None:
    slim = {
        "recorded_at": utc_now(),
        "ice_version": row.get("ice_version"),
        "template": row.get("template"),
        "framework_visible": row.get("framework_visible"),
        "citation_density": row.get("citation_density"),
        "narrative_style": row.get("narrative_style"),
        "validation_passed": (row.get("validation") or {}).get("passed"),
        "failures": (row.get("validation") or {}).get("failures") or [],
        "narrative_completeness": (row.get("validation") or {}).get("narrative_completeness"),
        "generic_template": row.get("generic_template"),
        "llm_used": row.get("llm_used"),
    }
    _ROWS.append(slim)
    if len(_ROWS) > _MAX:
        del _ROWS[: len(_ROWS) - _MAX]


def list_rows(*, limit: int = 100) -> list[dict[str, Any]]:
    return list(reversed(_ROWS[-limit:]))


def clear() -> None:
    _ROWS.clear()
