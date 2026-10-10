"""Regulator / government graph."""

from __future__ import annotations

from knowledge_graph.graph._edge import e, n

REG_NODES = [
    n("sebi", "SEBI", "regulator"),
    n("mca", "Ministry of Corporate Affairs", "government"),
    n("goi", "Government of India", "government"),
]

REG_EDGES = [
    e("HDFCBANK", "rbi", "regulated_by", strength=0.98, confidence=0.99, note="Banks regulated by RBI"),
    e("KOTAKBANK", "rbi", "regulated_by", strength=0.98, confidence=0.99),
    e("SBIN", "rbi", "regulated_by", strength=0.98, confidence=0.99),
    e("HDFCBANK", "sebi", "regulated_by", strength=0.85, confidence=0.95, note="Listed entity SEBI oversight"),
    e("TCS", "sebi", "regulated_by", strength=0.85, confidence=0.95),
    e("NESTLEIND", "sebi", "regulated_by", strength=0.85, confidence=0.95),
    e("goi", "sebi", "owns", strength=0.4, confidence=0.7),
]
