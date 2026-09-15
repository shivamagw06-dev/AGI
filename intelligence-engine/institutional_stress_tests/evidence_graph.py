"""Build a simple evidence graph from raw corpus — no conclusions."""

from __future__ import annotations

from typing import Any, Mapping


def build_evidence_graph(corpus: Mapping[str, Any]) -> dict[str, Any]:
    nodes = []
    edges = []
    docs = list(corpus.get("documents") or [])
    by_id = {d["evidence_id"]: d for d in docs if d.get("evidence_id")}

    for d in docs:
        eid = d["evidence_id"]
        nodes.append(
            {
                "id": eid,
                "type": d.get("evidence_type"),
                "date": d.get("date"),
                "source": d.get("source"),
                "ticker": d.get("ticker"),
                "peer_ticker": d.get("peer_ticker"),
                "confidence_contribution": d.get("confidence_contribution"),
            }
        )

    # Temporal edges
    dated = sorted(docs, key=lambda x: str(x.get("date") or ""))
    for a, b in zip(dated, dated[1:]):
        edges.append(
            {
                "from": a["evidence_id"],
                "to": b["evidence_id"],
                "relation": "precedes",
            }
        )

    # Peer links
    primary = str(corpus.get("ticker") or "").upper()
    event_nodes = [d["evidence_id"] for d in docs if d.get("evidence_type") in {"regulatory_filing", "exchange_announcement"}]
    for d in docs:
        if d.get("peer_ticker"):
            for ev in event_nodes[:1]:
                edges.append(
                    {
                        "from": ev,
                        "to": d["evidence_id"],
                        "relation": "peer_context_for_event",
                    }
                )

    # Call ↔ statement alignment candidates (same period window)
    calls = [d for d in docs if d.get("evidence_type") == "earnings_call"]
    stmts = [d for d in docs if d.get("evidence_type") in {"financial_statement", "quarterly_report"}]
    for c in calls:
        for s in stmts:
            if str(c.get("date") or "")[:7] == str(s.get("date") or "")[:7] or abs(
                _month_key(c.get("date")) - _month_key(s.get("date"))
            ) <= 1:
                edges.append(
                    {
                        "from": c["evidence_id"],
                        "to": s["evidence_id"],
                        "relation": "management_vs_financials_candidate",
                    }
                )

    types = {}
    for d in docs:
        types[d.get("evidence_type") or "unknown"] = types.get(d.get("evidence_type") or "unknown", 0) + 1

    return {
        "schema": "ist02.evidence_graph.v1",
        "ticker": primary,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": edges,
        "coverage_by_type": types,
        "evidence_ids": list(by_id.keys()),
        "orphan_conclusions": [],  # graph itself has no conclusions
    }


def _month_key(date_str: Any) -> int:
    s = str(date_str or "1970-01-01")
    try:
        y, m = int(s[0:4]), int(s[5:7])
        return y * 12 + m
    except Exception:
        return 0


def cite(evidence_id: str, corpus: Mapping[str, Any]) -> dict[str, Any]:
    """Canonical citation block for a statement."""
    for d in corpus.get("documents") or []:
        if d.get("evidence_id") == evidence_id:
            return {
                "evidence_id": d.get("evidence_id"),
                "evidence_source": d.get("source"),
                "evidence_date": d.get("date"),
                "evidence_type": d.get("evidence_type"),
                "confidence_contribution": d.get("confidence_contribution"),
            }
    return {
        "evidence_id": evidence_id,
        "evidence_source": None,
        "evidence_date": None,
        "evidence_type": None,
        "confidence_contribution": 0.0,
        "missing": True,
    }
