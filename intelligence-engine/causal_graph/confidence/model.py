"""Causal confidence — evidence, historical accuracy, current relevance."""

from __future__ import annotations

from typing import Any


def edge_score(edge: dict[str, Any]) -> float:
    conf = float(edge.get("confidence") or 0)
    hist = float(edge.get("historical_accuracy") or conf * 0.9)
    rel = float(edge.get("current_relevance") or 0.8)
    strength = float(edge.get("strength") or 0)
    years = float(edge.get("evidence_years") or 0)
    years_factor = min(1.0, years / 15.0)
    raw = 0.35 * conf + 0.25 * hist + 0.2 * rel + 0.1 * strength + 0.1 * years_factor
    return round(max(0.0, min(1.0, raw)), 3)


def causal_confidence(edges: list[dict[str, Any]], chains: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if not edges:
        return {
            "confidence": 0.0,
            "label": "insufficient",
            "edge_mean": 0.0,
            "chain_mean": 0.0,
            "components": {},
        }
    scores = [edge_score(e) for e in edges]
    edge_mean = sum(scores) / len(scores)
    chain_scores = []
    for c in chains or []:
        if c.get("path_confidence") is not None:
            chain_scores.append(float(c["path_confidence"]))
    chain_mean = sum(chain_scores) / len(chain_scores) if chain_scores else edge_mean
    overall = round(0.55 * edge_mean + 0.45 * chain_mean, 3)
    if overall >= 0.8:
        label = "high"
    elif overall >= 0.6:
        label = "moderate"
    elif overall >= 0.4:
        label = "low"
    else:
        label = "insufficient"
    return {
        "confidence": overall,
        "label": label,
        "edge_mean": round(edge_mean, 3),
        "chain_mean": round(chain_mean, 3),
        "components": {
            "evidence": round(sum(float(e.get("confidence") or 0) for e in edges) / len(edges), 3),
            "historical_accuracy": round(
                sum(float(e.get("historical_accuracy") or 0) for e in edges) / len(edges), 3
            ),
            "current_relevance": round(
                sum(float(e.get("current_relevance") or 0) for e in edges) / len(edges), 3
            ),
        },
        "rule": "Every causal edge stores confidence, evidence, historical accuracy, current relevance",
    }
