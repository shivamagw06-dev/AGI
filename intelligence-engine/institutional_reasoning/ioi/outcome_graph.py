"""Module 8 — Outcome Graph (OG).

Research DJG → PDG → Market Outcome → Framework Attribution → Review
"""

from __future__ import annotations

from typing import Any

OG_VERSION = "outcome-graph-v1.0.0"

NODE_KINDS = (
    "research_djg",
    "portfolio_decision_graph",
    "market_outcome",
    "prediction_evaluation",
    "framework_attribution",
    "review",
)

EDGE_KINDS = (
    "FEEDS",
    "REALISED_AS",
    "EVALUATED_BY",
    "ATTRIBUTED_BY",
    "REVIEWED_BY",
    "REFERENCES_DJG",
    "REFERENCES_PDG",
)


def _node(node_id: str, kind: str, label: str, **attrs: Any) -> dict[str, Any]:
    return {"id": node_id, "kind": kind, "label": label, "attrs": attrs}


def _edge(src: str, kind: str, dst: str, **attrs: Any) -> dict[str, Any]:
    return {"source": src, "kind": kind, "target": dst, "attrs": attrs}


def build_outcome_graph(record: dict[str, Any]) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    decision_id = str(record.get("decision_id") or "decision")
    lifecycle = record.get("lifecycle") or {}
    market = record.get("market") or {}
    evaluation = record.get("evaluation") or {}
    attribution = record.get("attribution") or {}
    review = record.get("review") or {}

    djg = lifecycle.get("research_djg")
    pdg = lifecycle.get("portfolio_djg")

    n_djg = "research_djg"
    nodes.append(_node(n_djg, "research_djg", f"DJG {djg}", reference=djg, valid=lifecycle.get("research_djg_integrity")))

    n_pdg = "portfolio_decision_graph"
    nodes.append(_node(n_pdg, "portfolio_decision_graph", f"PDG {pdg}", reference=pdg, valid=lifecycle.get("portfolio_djg_integrity")))
    edges.append(_edge(n_djg, "FEEDS", n_pdg))
    if djg:
        edges.append(_edge(n_pdg, "REFERENCES_DJG", n_djg))

    n_mkt = "market_outcome"
    nodes.append(
        _node(
            n_mkt,
            "market_outcome",
            f"Outcome {lifecycle.get('ticker')}",
            total_return=market.get("total_return"),
            alpha=market.get("alpha"),
            found=market.get("found"),
        )
    )
    edges.append(_edge(n_pdg, "REALISED_AS", n_mkt))
    if pdg:
        edges.append(_edge(n_mkt, "REFERENCES_PDG", n_pdg))

    n_eval = "prediction_evaluation"
    nodes.append(
        _node(
            n_eval,
            "prediction_evaluation",
            f"Score {evaluation.get('score')}",
            grade=evaluation.get("grade"),
            return_error=evaluation.get("return_error"),
        )
    )
    edges.append(_edge(n_mkt, "EVALUATED_BY", n_eval))

    n_attr = "framework_attribution"
    primary = attribution.get("primary_failure") or {}
    nodes.append(
        _node(
            n_attr,
            "framework_attribution",
            primary.get("label") or "Attribution",
            wrong=attribution.get("wrong") or [],
            unattributed=attribution.get("unattributed"),
        )
    )
    edges.append(_edge(n_eval, "ATTRIBUTED_BY", n_attr))

    n_rev = "review"
    overall = (review.get("overall_quality") or {}).get("grade")
    nodes.append(
        _node(
            n_rev,
            "review",
            f"Review {overall}",
            overall=(review.get("overall_quality") or {}),
            learning_applied=False,
        )
    )
    edges.append(_edge(n_attr, "REVIEWED_BY", n_rev))

    node_ids = {n["id"] for n in nodes}
    problems: list[str] = []
    for e in edges:
        if e["source"] not in node_ids or e["target"] not in node_ids:
            problems.append(f"dangling_edge:{e['source']}->{e['target']}")
    required = set(NODE_KINDS)
    missing = sorted(required - node_ids)
    if missing:
        problems.append(f"missing_nodes:{missing}")
    if not djg:
        problems.append("missing_djg_link")
    if not pdg:
        problems.append("missing_pdg_link")
    if attribution.get("unattributed"):
        problems.append("unattributed_failure")

    return {
        "og_version": OG_VERSION,
        "decision_id": decision_id,
        "ticker": lifecycle.get("ticker"),
        "djg_reference": djg,
        "pdg_reference": pdg,
        "nodes": nodes,
        "edges": edges,
        "terminal": n_rev,
        "node_kinds": sorted({n["kind"] for n in nodes}),
        "edge_kinds": sorted({e["kind"] for e in edges}),
        "counts": {"nodes": len(nodes), "edges": len(edges)},
        "integrity": {
            "valid": not problems,
            "problems": problems,
            "linked_to_djg": bool(djg),
            "linked_to_pdg": bool(pdg),
            "complete_lifecycle": not missing and bool(djg) and bool(pdg),
        },
    }
