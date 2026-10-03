"""PKG-01 diagnostics and quality gates."""

from __future__ import annotations

from typing import Any, List

from institutional_portfolio.portfolio_graph import PortfolioKnowledgeGraph
from institutional_portfolio.schema import PKG_VERSION, PKG_WORKSTREAM_ID


def quality_gates(graph: PortfolioKnowledgeGraph) -> tuple[dict[str, bool], list[str]]:
    errors: list[str] = []
    ip = graph.institutional_portfolio
    has_portfolio = bool(graph.portfolio_node_id and graph.nodes_by_type("Portfolio"))
    has_companies = bool(graph.nodes_by_type("Company"))
    has_holdings = bool(graph.nodes_by_type("Holding"))
    has_allocations = bool(ip and ip.allocations)
    has_exposures = bool(ip and ip.exposures)
    has_lineage = bool(graph.lineage)
    has_relationships = bool(graph.relationships)

    if not has_portfolio:
        errors.append("no portfolio node")
    if not has_companies:
        errors.append("no company nodes")
    if not has_holdings:
        errors.append("no holding nodes")
    if not has_allocations:
        errors.append("no allocations")
    if not has_exposures:
        errors.append("no exposures")
    if not has_lineage:
        errors.append("no lineage")
    if not has_relationships:
        errors.append("no relationships")

    # Weights should approximately sum with cash to ~1.0
    if ip:
        equity = sum(float(h.weight) for h in ip.holdings)
        total = equity + float(ip.cash_weight or 0.0)
        if total <= 0:
            errors.append("zero portfolio weight")
        elif abs(total - 1.0) > 0.05:
            errors.append(f"weights sum {total:.3f} outside tolerance")

    gates = {
        "has_portfolio": has_portfolio,
        "has_companies": has_companies,
        "has_holdings": has_holdings,
        "has_allocations": has_allocations,
        "has_exposures": has_exposures,
        "has_lineage": has_lineage,
        "has_relationships": has_relationships,
        "weights_sane": "zero portfolio weight" not in errors
        and not any(e.startswith("weights sum") for e in errors),
    }
    return gates, errors


def build_diagnostics(graph: PortfolioKnowledgeGraph) -> dict[str, Any]:
    gates, errors = quality_gates(graph)
    by_type: dict[str, int] = {}
    for n in graph.nodes.values():
        by_type[n.type] = by_type.get(n.type, 0) + 1
    ip = graph.institutional_portfolio
    return {
        "workstream_id": PKG_WORKSTREAM_ID,
        "version": PKG_VERSION,
        "portfolio_id": graph.portfolio_id,
        "graph_id": graph.graph_id,
        "entity_count": len(graph.nodes),
        "relationship_count": len(graph.relationships),
        "entities_by_type": by_type,
        "holding_count": len(ip.holdings) if ip else 0,
        "risk_count": len(ip.risks) if ip else 0,
        "decision_count": len(ip.decisions) if ip else 0,
        "quality_gates": gates,
        "validation_errors": errors,
        "passed": not errors,
        "concentration": (graph.meta or {}).get("concentration"),
        "average_correlation": (graph.meta or {}).get("average_correlation"),
        "lineage": list(graph.lineage),
        "llm": False,
    }


def validate_graph(graph: PortfolioKnowledgeGraph) -> List[str]:
    _, errors = quality_gates(graph)
    return errors
