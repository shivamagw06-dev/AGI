"""Temporal edge metadata — start/end/active/historical/deprecated."""

from __future__ import annotations

from typing import Any


def with_temporal(
    edge: dict[str, Any],
    *,
    start: str = "2015-01-01",
    end: str | None = None,
    active: bool = True,
    historical: bool = False,
    deprecated: bool = False,
) -> dict[str, Any]:
    out = dict(edge)
    out.setdefault("start_date", start)
    out.setdefault("end_date", end)
    out.setdefault("active", active and not deprecated)
    out.setdefault("historical", historical or (end is not None))
    out.setdefault("deprecated", deprecated)
    out.setdefault("confidence_evolution", [
        {"as_of": start, "confidence": float(edge.get("confidence") or 0.7)}
    ])
    return out
