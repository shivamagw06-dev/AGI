"""Technology ecosystem graph."""

from __future__ import annotations

from knowledge_graph.graph._edge import e, n

TECH_NODES = [
    n("tech_cloud", "Cloud Computing", "technology"),
    n("tech_ai", "Artificial Intelligence", "technology"),
    n("tech_payments", "Digital Payments", "technology"),
    n("tech_core_banking", "Core Banking Systems", "technology"),
]

TECH_EDGES = [
    e("tech_cloud", "TCS", "drives", strength=0.7, confidence=0.88),
    e("tech_ai", "TCS", "drives", strength=0.65, confidence=0.86),
    e("tech_ai", "ai_infra", "depends_on", strength=0.8, confidence=0.9),
    e("tech_payments", "HDFCBANK", "drives", strength=0.75, confidence=0.9),
    e("tech_core_banking", "HDFCBANK", "depends_on", strength=0.7, confidence=0.88),
    e("semiconductor", "tech_ai", "supplies", strength=0.85, confidence=0.92),
    e("nvidia", "tech_ai", "drives", strength=0.9, confidence=0.95),
]
