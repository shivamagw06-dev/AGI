"""Optional soft bridge for FIRE to consume FKB without redesign.

FIRE modules may import helpers from here gradually. This module never
executes analysis — it only exposes knowledge lookups and threshold values.
"""

from __future__ import annotations

from typing import Any

from financial_knowledge.registry import knowledge


def narrative_template(relationship_id: str) -> str | None:
    row = knowledge.relationship(relationship_id)
    return None if not row else str(row.get("narrative_template") or "")


def threshold_value(name: str, *, sector: str | None = None, default: float | None = None) -> float | None:
    row = knowledge.threshold(name, sector=sector)
    if not row:
        return default
    val = row.get("value")
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def relationship_ids() -> list[str]:
    return [r["id"] for r in knowledge.list_relationships()]


def metric_definition(name: str) -> dict[str, Any] | None:
    return knowledge.metric(name)
