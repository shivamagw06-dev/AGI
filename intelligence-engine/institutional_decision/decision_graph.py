"""Decision graph — transparent factor path into recommendation."""

from __future__ import annotations

from typing import Any

from institutional_decision.models import DecisionGraph
from institutional_decision.schema import DECISION_GRAPH_NODES, DECISION_GRAPH_VERSION


def build_decision_graph(
    *,
    business_quality: str,
    financial_quality: str,
    valuation: str,
    risk: str,
    macro: str,
    management: str,
    recommendation: str,
    score: int,
    rule_path: str,
) -> DecisionGraph:
    values = {
        "business_quality": business_quality,
        "financial_quality": financial_quality,
        "valuation": valuation,
        "risk": risk,
        "macro": macro,
        "management": management,
        "recommendation": recommendation,
    }
    nodes: list[dict[str, Any]] = []
    for i, key in enumerate(DECISION_GRAPH_NODES):
        nodes.append(
            {
                "order": i + 1,
                "node": key,
                "value": values[key],
                "feeds": DECISION_GRAPH_NODES[i + 1] if i + 1 < len(DECISION_GRAPH_NODES) else None,
            }
        )
    nodes.append(
        {
            "order": len(nodes) + 1,
            "node": "score",
            "value": score,
            "rule_path": rule_path,
            "feeds": None,
        }
    )
    return DecisionGraph(nodes=tuple(nodes), version=DECISION_GRAPH_VERSION)
