"""Shared edge constructor for seeded institutional relationships."""

from __future__ import annotations

from typing import Any

from knowledge_graph.history.temporal import with_temporal


def e(
    source: str,
    target: str,
    relation: str,
    *,
    strength: float = 0.7,
    confidence: float = 0.85,
    evidence_years: int = 8,
    start: str = "2018-01-01",
    end: str | None = None,
    active: bool = True,
    historical: bool = False,
    note: str = "",
    evidence_kind: str = "institutional_prior",
    evidence_source: str = "knowledge_graph.seed",
) -> dict[str, Any]:
    edge = {
        "source": source,
        "target": target,
        "relation": relation,
        "direction": "directed",
        "strength": round(strength, 3),
        "confidence": round(confidence, 3),
        "evidence_years": evidence_years,
        "historical_accuracy": round(min(0.95, confidence - 0.03), 3),
        "current_relevance": 0.88 if active else 0.55,
        "validated": True,
        "evidence": [
            {
                "kind": evidence_kind,
                "source": evidence_source,
                "span_years": evidence_years,
                "note": note or f"{source} {relation} {target}",
            }
        ],
    }
    return with_temporal(
        edge,
        start=start,
        end=end,
        active=active,
        historical=historical or (end is not None),
    )


def n(
    id_: str,
    label: str,
    type_: str,
    *,
    aliases: list[str] | None = None,
    ticker: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    row = {
        "id": id_,
        "label": label,
        "type": type_,
        "aliases": aliases or [],
        "canonical": True,
    }
    if ticker:
        row["ticker"] = ticker
    row.update(extra)
    return row
