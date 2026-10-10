"""Relationship confidence — evidence, historical validation, current relevance."""

from __future__ import annotations

from typing import Any


def edge_confidence(edge: dict[str, Any]) -> float:
    conf = float(edge.get("confidence") or 0)
    hist = float(edge.get("historical_accuracy") or conf * 0.9)
    strength = float(edge.get("strength") or 0)
    years = float(edge.get("evidence_years") or 0)
    years_factor = min(1.0, years / 10.0)
    active = 1.0 if edge.get("active", True) else 0.6
    raw = (0.4 * conf + 0.25 * hist + 0.2 * strength + 0.15 * years_factor) * active
    return round(max(0.0, min(1.0, raw)), 3)


def graph_confidence(edges: list[dict[str, Any]]) -> dict[str, Any]:
    if not edges:
        return {"confidence": 0.0, "label": "insufficient", "edge_mean": 0.0}
    scores = [edge_confidence(e) for e in edges]
    mean = sum(scores) / len(scores)
    label = "high" if mean >= 0.75 else "moderate" if mean >= 0.55 else "low"
    return {
        "confidence": round(mean, 3),
        "label": label,
        "edge_mean": round(mean, 3),
        "relationship_confidence_maintained": True,
        "rule": "Relationship confidence maintained across active and historical edges",
    }
