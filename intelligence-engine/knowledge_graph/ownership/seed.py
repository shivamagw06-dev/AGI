"""Ownership / board interlock graph."""

from __future__ import annotations

from knowledge_graph.graph._edge import e, n

OWNERSHIP_NODES = [
    n("promoter_hdfc", "HDFC Bank Promoter / Institutional Core", "person", role="promoter_group"),
    n("fii_india", "Foreign Institutional Investors (India)", "etf", role="investor_class"),
    n("mf_india", "Indian Mutual Funds", "etf", role="investor_class"),
    n("tata_sons", "Tata Sons", "company", role="promoter"),
    n("nse", "National Stock Exchange of India", "exchange"),
    n("bse", "BSE", "exchange"),
]

OWNERSHIP_EDGES = [
    e("tata_sons", "TCS", "owns", strength=0.9, confidence=0.95, note="Promoter ownership via Tata Sons"),
    e("tata_sons", "TATASTEEL", "owns", strength=0.85, confidence=0.93),
    e("tata_sons", "TATAMOTORS", "owns", strength=0.85, confidence=0.93),
    e("fii_india", "HDFCBANK", "invests_in", strength=0.7, confidence=0.88),
    e("mf_india", "HDFCBANK", "invests_in", strength=0.75, confidence=0.9),
    e("mf_india", "TCS", "invests_in", strength=0.72, confidence=0.89),
    e("fii_india", "INFY", "invests_in", strength=0.7, confidence=0.88),
    e("HDFCBANK", "nse", "listed_on", strength=0.99, confidence=0.99),
    e("HDFCBANK", "bse", "listed_on", strength=0.99, confidence=0.99),
    e("TCS", "nse", "listed_on", strength=0.99, confidence=0.99),
    e("NESTLEIND", "nse", "listed_on", strength=0.99, confidence=0.99),
]
