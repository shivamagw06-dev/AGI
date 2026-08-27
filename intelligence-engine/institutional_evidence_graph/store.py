"""In-memory IEG telemetry store."""

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
        "ieg_version": row.get("ieg_version"),
        "graph_id": row.get("graph_id"),
        "entities": row.get("entities") or [],
        "n_nodes": row.get("n_nodes"),
        "n_edges": row.get("n_edges"),
        "domain_coverage_pct": row.get("domain_coverage_pct"),
        "n_chains": len(row.get("chains") or []),
        "as_of": row.get("as_of"),
        "playbook_id": row.get("playbook_id"),
        "validation_passed": (row.get("validation") or {}).get("passed"),
        "guides_evidence": True,
    }
    _ROWS.append(slim)
    if len(_ROWS) > _MAX:
        del _ROWS[: len(_ROWS) - _MAX]


def list_rows(*, limit: int = 100) -> list[dict[str, Any]]:
    return list(reversed(_ROWS[-limit:]))


def clear() -> None:
    _ROWS.clear()
