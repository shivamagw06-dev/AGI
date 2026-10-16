"""KG-01 impact engine — every key node stores an Impact Score."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict

from institutional_decision.recommendation_rules import business_quality_band_safe
from institutional_graph.graph import InstitutionalKnowledgeGraph
from institutional_reporting.models import InstitutionalReportInput


def _bq_points(payload: InstitutionalReportInput) -> int:
    try:
        n = float(payload.business_quality)
        if n >= 93:
            return 20
        if n >= 88:
            return 18
        if n >= 75:
            return 12
        if n >= 60:
            return 6
        return 0
    except (TypeError, ValueError):
        band = business_quality_band_safe(payload.business_quality)
        return {"Excellent": 20, "Strong": 18, "Adequate": 10, "Weak": 0}.get(band, 8)


def compute_impacts(
    graph: InstitutionalKnowledgeGraph,
    evidence: InstitutionalReportInput,
) -> Dict[str, int]:
    """
    Compute and store impact scores on key nodes.

    Example:
      Business Quality +18
      Financial Quality +15
      Valuation −8
      Macro −4
      Risk −6
      Governance +7
    """
    fq = str(evidence.financial_quality or "").strip().title()
    fq_pts = {"Excellent": 18, "Strong": 15, "Stable": 10, "Weak": -6, "Unclear": 0}.get(fq, 5)
    val = str(evidence.valuation or "").strip().title()
    val_pts = {"Cheap": 12, "Fair": 2, "Expensive": -8, "Unclear": -2}.get(val, 0)
    risk = str(evidence.overall_risk or "").strip().title()
    risk_pts = {"Low": 8, "Moderate": -4, "High": -10, "Severe": -14}.get(risk, -2)
    # Aggregate named risk nodes: each contributes mild pressure beyond overall
    risk_nodes = graph.nodes_by_type("Risk")
    risk_extra = -min(6, max(0, len(risk_nodes) - 1) * 2)
    risk_total = risk_pts + risk_extra
    macro_pts = -4 if "bank" in str(evidence.sector or "").lower() else -2
    bq_pts = _bq_points(evidence)
    gov_pts = 7 if bq_pts >= 18 else 5
    profit_pts = max(-8, min(16, (fq_pts + bq_pts) // 2 - 2))

    scores = {
        "business_quality": bq_pts,
        "financial_quality": fq_pts,
        "valuation": val_pts,
        "macro": macro_pts,
        "risk": risk_total,
        "governance": gov_pts,
        "profitability": profit_pts,
        "nim": 6 if fq_pts >= 10 else 2,
        "credit_cost": -5 if risk_total < 0 else 2,
        "roe": 8 if fq_pts >= 15 else 4,
    }

    metric_ids = (graph.meta or {}).get("metric_ids") or {}
    label_to_key = {
        "Business Quality": "business_quality",
        "Financial Quality": "financial_quality",
        "Profitability": "profitability",
        "Net Interest Margin": "nim",
        "Credit Cost": "credit_cost",
        "Return on Equity": "roe",
    }

    # Apply to metric nodes
    for key, node_id in metric_ids.items():
        node = graph.get(node_id)
        if node is None:
            continue
        pts = int(scores.get(key, 0))
        graph.nodes[node_id] = replace(node, impact_score=pts)

    # Valuation node
    val_id = (graph.meta or {}).get("valuation_node_id")
    if val_id and graph.get(val_id):
        graph.nodes[val_id] = replace(graph.get(val_id), impact_score=val_pts)  # type: ignore[arg-type]

    # Macro (RBI)
    rbi_id = (graph.meta or {}).get("rbi_node_id")
    if rbi_id and graph.get(rbi_id):
        graph.nodes[rbi_id] = replace(graph.get(rbi_id), impact_score=macro_pts)  # type: ignore[arg-type]

    # Management / governance
    for node in graph.nodes_by_type("Management"):
        graph.nodes[node.id] = replace(node, impact_score=gov_pts)

    # Risk nodes share total
    if risk_nodes:
        per = int(round(risk_total / max(1, len(risk_nodes))))
        for node in risk_nodes:
            graph.nodes[node.id] = replace(node, impact_score=per)

    # Decision impact = sum of major factors (stored on decision node)
    if graph.decision_node_id and graph.get(graph.decision_node_id):
        total = bq_pts + fq_pts + val_pts + macro_pts + risk_total + gov_pts
        dnode = graph.get(graph.decision_node_id)
        assert dnode is not None
        graph.nodes[graph.decision_node_id] = replace(dnode, impact_score=total)

    graph.meta["impact_scores"] = scores
    graph.meta["impact_total"] = (
        bq_pts + fq_pts + val_pts + macro_pts + risk_total + gov_pts
    )
    # Silence unused
    _ = label_to_key
    return scores


def impact_summary(graph: InstitutionalKnowledgeGraph) -> dict[str, Any]:
    scores = dict((graph.meta or {}).get("impact_scores") or {})
    return {
        "Business Quality": scores.get("business_quality", 0),
        "Financial Quality": scores.get("financial_quality", 0),
        "Valuation": scores.get("valuation", 0),
        "Macro": scores.get("macro", 0),
        "Risk": scores.get("risk", 0),
        "Governance": scores.get("governance", 0),
        "total": (graph.meta or {}).get("impact_total", 0),
    }
