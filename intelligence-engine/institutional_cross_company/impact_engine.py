"""CCI-01 Impact Engine — which companies / holdings are affected by a driver."""

from __future__ import annotations

from typing import Any, Optional

from institutional_cross_company.propagation import propagate
from institutional_cross_company.relationship_engine import relationships_for_company, relationships_for_macro


def impact_query(
    *,
    driver: str = "",
    ticker: str = "",
    portfolio_id: str = "agi-core-equity",
) -> dict[str, Any]:
    """
    Oil ↑ → Relationship Graph (via providers) → Affected Companies → Portfolio → Risk → Committee

    Structural impact mapping only — not a price or recommendation forecast.
    """
    d = str(driver or "").strip()
    t = str(ticker or "").upper().strip()

    if d:
        prop = propagate(d, portfolio_id=portfolio_id)
        rels = relationships_for_macro(prop.driver)
        return {
            "ok": True,
            "question": f"Which companies are affected by {prop.driver}?",
            "driver": prop.driver,
            "propagation": prop.to_dict(),
            "relationships": [r.to_dict() for r in rels[:50]],
            "affected_companies": list(prop.affected_entities),
            "portfolio_holdings": list(prop.portfolio_holdings),
            "downstream": ["Portfolio Holdings", "Risk (PRE-01)", "Policy (PCE-01)", "Committee (ICE-01)"],
            "predictive": False,
            "generates_recommendations": False,
            "owns_graph": False,
            "graph_system_of_record": "KG-01",
        }

    if t:
        rels = relationships_for_company(t, portfolio_id=portfolio_id)
        competitors = [r.target_entity for r in rels if r.relationship_type == "competitor"]
        macros = [r.target_entity for r in rels if r.category == "macro"]
        return {
            "ok": True,
            "question": f"How does {t} affect everything else?",
            "ticker": t,
            "competitors": competitors,
            "macro_drivers": macros,
            "relationships": [r.to_dict() for r in rels],
            "downstream": ["Sector peers", "Portfolio co-holdings", "Shared macro risks"],
            "predictive": False,
            "generates_recommendations": False,
            "owns_graph": False,
            "graph_system_of_record": "KG-01",
        }

    return {"ok": False, "error": "driver or ticker required", "owns_graph": False}


def oil_shock_example(pct: float = 20.0) -> dict[str, Any]:
    pack = impact_query(driver="oil")
    pack["scenario"] = {
        "driver": "oil",
        "move_pct": pct,
        "note": "Dependency map only — magnitude is contextual, not a CCI forecast",
    }
    return pack
