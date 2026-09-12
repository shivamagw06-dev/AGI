"""Macro knowledge graph — rates, inflation, commodities → industries → companies."""

from __future__ import annotations

from knowledge_graph.graph._edge import e, n

MACRO_NODES = [
    n("oil", "Crude Oil", "commodity", family="energy"),
    n("copper", "Copper", "commodity", family="metals"),
    n("steel", "Steel", "commodity", family="metals"),
    n("usd", "US Dollar", "currency"),
    n("inr", "Indian Rupee", "currency"),
    n("repo_rate", "RBI Repo Rate", "interest_rate"),
    n("india_cpi", "India CPI Inflation", "inflation"),
    n("india_10y", "India 10Y Yield", "interest_rate"),
    n("rbi", "Reserve Bank of India", "central_bank"),
    n("india", "India", "country"),
    n("china", "China", "country"),
    n("usa", "United States", "country"),
]

MACRO_EDGES = [
    e("rbi", "repo_rate", "drives", strength=0.98, confidence=0.99, note="RBI sets policy repo"),
    e("oil", "india_cpi", "drives", strength=0.82, confidence=0.91, evidence_years=15),
    e("india_cpi", "repo_rate", "affected_by", strength=0.7, confidence=0.86, note="Inflation feeds policy reaction"),
    e("repo_rate", "sector_banks", "drives", strength=0.8, confidence=0.9),
    e("repo_rate", "HDFCBANK", "affected_by", strength=0.78, confidence=0.9),
    e("usd", "sector_it", "drives", strength=0.76, confidence=0.9),
    e("usd", "TCS", "affected_by", strength=0.74, confidence=0.89),
    e("inr", "sector_fmcg", "affected_by", strength=0.65, confidence=0.84, note="INR weakness → imported inflation"),
    e("inr", "NESTLEIND", "affected_by", strength=0.6, confidence=0.82),
    e("china", "copper", "drives", strength=0.8, confidence=0.9),
    e("china", "steel", "drives", strength=0.76, confidence=0.88),
    e("copper", "sector_metals", "drives", strength=0.7, confidence=0.86),
    e("steel", "TATASTEEL", "drives", strength=0.88, confidence=0.94),
    e("steel", "TATAMOTORS", "depends_on", strength=0.62, confidence=0.84, note="Auto OEM steel dependency"),
    e("oil", "RELIANCE", "drives", strength=0.8, confidence=0.9),
    e("india", "rbi", "owns", strength=0.5, confidence=0.7, note="Sovereign institutional context"),
]
