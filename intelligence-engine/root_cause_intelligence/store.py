"""In-process RCI analysis store."""

from __future__ import annotations

from copy import deepcopy
from threading import Lock
from typing import Any

_LOCK = Lock()
_ROWS: list[dict[str, Any]] = []
_MAX = 50


def record(analysis: dict[str, Any]) -> dict[str, Any]:
    light = {k: v for k, v in analysis.items() if k not in {"failures_sample"}}
    # keep compact cluster list
    light["top_10_clusters"] = [
        {
            "cluster_id": c.get("cluster_id"),
            "cluster_key": c.get("cluster_key"),
            "count": c.get("count"),
            "root_cause": c.get("root_cause"),
            "sector": c.get("sector"),
            "framework_family": c.get("framework_family"),
            "severity": c.get("severity"),
            "impact_statement": c.get("impact_statement"),
            "suggested_fix_title": (c.get("suggested_fix") or {}).get("title"),
        }
        for c in (analysis.get("top_10_clusters") or [])
    ]
    with _LOCK:
        _ROWS.append(light)
        if len(_ROWS) > _MAX:
            del _ROWS[: len(_ROWS) - _MAX]
    return deepcopy(light)


def list_analyses(*, limit: int = 20) -> list[dict[str, Any]]:
    with _LOCK:
        rows = list(_ROWS)
    return deepcopy(list(reversed(rows[-max(1, min(int(limit), 50)) :])))


def latest() -> dict[str, Any] | None:
    rows = list_analyses(limit=1)
    return rows[0] if rows else None
