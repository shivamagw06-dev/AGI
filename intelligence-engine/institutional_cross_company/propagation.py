"""CCI-01 Propagation Engine — dependency propagation, not prediction."""

from __future__ import annotations

from typing import Any, Optional

from institutional_cross_company.dependency import dependency_map
from institutional_cross_company.models import PropagationResult
from institutional_cross_company.relationship_engine import relationships_for_macro


def propagate(
    driver: str,
    *,
    portfolio_id: str = "agi-core-equity",
    holdings: Optional[list[str]] = None,
) -> PropagationResult:
    """
    Example:
      RBI cuts rates → Banking Sector → NIMs → Company Decisions → Portfolio Decisions

    CCI emits the dependency path. It does not invent the decision outcomes.
    """
    dep = dependency_map(driver)
    companies = list(dep.get("companies") or [])
    held = _portfolio_overlap(companies, portfolio_id=portfolio_id, holdings=holdings)
    rels = relationships_for_macro(str(dep.get("driver") or driver))
    paths = [
        {
            "from": r.source_entity,
            "to": r.target_entity,
            "type": r.relationship_type,
            "path": list(r.propagation_path),
        }
        for r in rels[:40]
    ]
    steps = tuple(dep.get("steps") or ())
    return PropagationResult(
        driver=str(dep.get("driver") or driver),
        steps=steps,
        affected_entities=tuple(companies),
        portfolio_holdings=tuple(held),
        path_summaries=tuple(paths),
        predictive=False,
        diagnostics={
            "dependency_ok": bool(dep.get("ok")),
            "relationship_count": len(rels),
            "owns_graph": False,
            "graph_system_of_record": "KG-01",
        },
    )


def _portfolio_overlap(
    companies: list[str],
    *,
    portfolio_id: str,
    holdings: Optional[list[str]] = None,
) -> list[str]:
    if holdings is not None:
        held_set = {str(h).upper() for h in holdings}
        return sorted(c for c in companies if c in held_set)

    held: list[str] = []
    try:
        from institutional_portfolio.production import get_portfolio_graph

        g = get_portfolio_graph(portfolio_id, include_company_graphs=False)
        graph = (g or {}).get("graph") or g or {}
        for h in graph.get("holdings") or graph.get("positions") or []:
            ht = str(h.get("ticker") if isinstance(h, dict) else h or "").upper()
            if ht:
                held.append(ht)
    except Exception:
        held = ["HDFCBANK", "ICICIBANK", "KOTAKBANK", "AXISBANK", "TCS", "INFY"]
    held_set = set(held)
    return sorted(c for c in companies if c in held_set)


def propagate_pack(driver: str, **kwargs: Any) -> dict[str, Any]:
    return propagate(driver, **kwargs).to_dict()
