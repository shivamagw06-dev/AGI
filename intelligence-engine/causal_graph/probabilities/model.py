"""Simple transmission probability from edge strength × confidence."""

from __future__ import annotations

from typing import Any


def edge_probability(edge: dict[str, Any]) -> float:
    strength = float(edge.get("strength") or 0)
    confidence = float(edge.get("confidence") or 0)
    relevance = float(edge.get("current_relevance") or 0.8)
    return round(max(0.0, min(1.0, strength * confidence * (0.7 + 0.3 * relevance))), 3)


def chain_probability(edges: list[dict[str, Any]]) -> float:
    if not edges:
        return 0.0
    p = 1.0
    for e in edges:
        p *= edge_probability(e)
    # Soften compound decay for multi-hop institutional chains
    hops = len(edges)
    soften = 0.55 + 0.45 * (1.0 / hops)
    return round(max(0.0, min(1.0, p**soften if p > 0 else 0.0)), 3)
