"""Event graph — budget / rates / shocks create relationships."""

from __future__ import annotations

from knowledge_graph.graph._edge import e, n

EVENT_NODES = [
    n("event_union_budget", "Union Budget", "event"),
    n("event_tax_change", "Tax Change", "event"),
    n("event_rbi_rate_hike", "RBI Rate Hike Cycle", "event"),
    n("event_oil_shock", "Oil Shock", "event"),
    n("event_consumption", "Consumption Impulse", "event"),
]

EVENT_EDGES = [
    e("event_union_budget", "event_tax_change", "drives", strength=0.8, confidence=0.9),
    e("event_tax_change", "event_consumption", "drives", strength=0.65, confidence=0.84),
    e("event_consumption", "sector_fmcg", "drives", strength=0.7, confidence=0.86),
    e("event_consumption", "NESTLEIND", "affected_by", strength=0.68, confidence=0.85),
    e("event_rbi_rate_hike", "repo_rate", "drives", strength=0.9, confidence=0.95),
    e("event_rbi_rate_hike", "sector_banks", "affected_by", strength=0.85, confidence=0.93),
    e("event_rbi_rate_hike", "HDFCBANK", "affected_by", strength=0.82, confidence=0.92),
    e("event_oil_shock", "oil", "drives", strength=0.95, confidence=0.97),
    e("event_oil_shock", "india_cpi", "drives", strength=0.8, confidence=0.9),
    e("event_oil_shock", "NESTLEIND", "affected_by", strength=0.6, confidence=0.84),
]
