"""Macro causal edges — institutional priors with evidence metadata."""

from __future__ import annotations

from typing import Any

MACRO_NODES: list[dict[str, Any]] = []


def _e(
    source: str,
    target: str,
    *,
    strength: float,
    confidence: float,
    evidence_years: int,
    relation: str = "influences",
    direction_sign: int = 1,
    historical_accuracy: float = 0.78,
    current_relevance: float = 0.85,
    notes: str = "",
) -> dict[str, Any]:
    return {
        "source": source,
        "target": target,
        "relation": relation,
        "direction": "directed",
        "direction_sign": direction_sign,  # +1 same direction, -1 inverse
        "strength": round(strength, 3),
        "confidence": round(confidence, 3),
        "evidence_years": evidence_years,
        "historical_accuracy": round(historical_accuracy, 3),
        "current_relevance": round(current_relevance, 3),
        "evidence": [
            {
                "kind": "historical_series",
                "span_years": evidence_years,
                "note": notes or f"{source} → {target} institutional prior",
                "source": "causal_graph.macro_links",
            }
        ],
        "validated": True,
    }


MACRO_EDGES: list[dict[str, Any]] = [
    _e("oil", "india_cpi", strength=0.82, confidence=0.91, evidence_years=15, notes="Oil pass-through into India CPI"),
    _e("oil", "imported_inflation", strength=0.88, confidence=0.93, evidence_years=15),
    _e("india_cpi", "india_10y", strength=0.74, confidence=0.86, evidence_years=12, notes="Inflation premium in bond yields"),
    _e("india_10y", "cost_of_equity", strength=0.79, confidence=0.88, evidence_years=12),
    _e("cost_of_equity", "bank_multiple", strength=0.71, confidence=0.84, evidence_years=10, direction_sign=-1),
    _e("us_10y", "cost_of_equity", strength=0.62, confidence=0.8, evidence_years=15, notes="Global discount-rate spillover"),
    _e("us_10y", "usd", strength=0.55, confidence=0.78, evidence_years=15),
    _e("repo_rate", "nim", strength=0.76, confidence=0.89, evidence_years=14, notes="Policy rate → bank NIM lag"),
    _e("repo_rate", "credit_growth", strength=0.68, confidence=0.85, evidence_years=14, direction_sign=-1),
    _e("nim", "roe", strength=0.8, confidence=0.9, evidence_years=14),
    _e("roe", "bank_multiple", strength=0.77, confidence=0.88, evidence_years=12),
    _e("credit_growth", "sector_housing", strength=0.72, confidence=0.86, evidence_years=12),
    _e("sector_housing", "sector_cement", strength=0.7, confidence=0.84, evidence_years=12),
    _e("sector_cement", "steel", strength=0.58, confidence=0.8, evidence_years=10),
    _e("steel", "sector_capital_goods", strength=0.55, confidence=0.78, evidence_years=10),
    _e("inr", "imported_inflation", strength=0.81, confidence=0.9, evidence_years=15, direction_sign=-1, notes="Rupee weakness raises import prices"),
    _e("imported_inflation", "consumer_spending", strength=0.64, confidence=0.82, evidence_years=12, direction_sign=-1),
    _e("consumer_spending", "fmcg_margins", strength=0.66, confidence=0.83, evidence_years=12),
    _e("usd", "it_revenue", strength=0.78, confidence=0.9, evidence_years=15, notes="INR weakness / USD strength lifts reported IT revenue"),
    _e("it_revenue", "it_margins", strength=0.6, confidence=0.8, evidence_years=12),
    _e("it_margins", "it_cash_flow", strength=0.75, confidence=0.87, evidence_years=12),
    _e("it_cash_flow", "it_multiple", strength=0.62, confidence=0.81, evidence_years=10),
    _e("china_economy", "copper", strength=0.8, confidence=0.9, evidence_years=15),
    _e("china_economy", "steel", strength=0.76, confidence=0.88, evidence_years=15),
    _e("copper", "metal_margins", strength=0.7, confidence=0.85, evidence_years=12),
    _e("steel", "metal_margins", strength=0.74, confidence=0.87, evidence_years=12),
    _e("metal_margins", "metal_earnings", strength=0.82, confidence=0.9, evidence_years=12),
    _e("demand", "orders", strength=0.77, confidence=0.86, evidence_years=8),
    _e("orders", "contribution_margin", strength=0.65, confidence=0.8, evidence_years=8),
    _e("contribution_margin", "fcf", strength=0.7, confidence=0.84, evidence_years=8),
    _e("rbi", "repo_rate", strength=0.95, confidence=0.98, evidence_years=20, relation="sets"),
    _e("fed", "us_fed_funds", strength=0.95, confidence=0.98, evidence_years=20, relation="sets"),
    _e("us_fed_funds", "us_10y", strength=0.72, confidence=0.88, evidence_years=20),
    _e("oil", "systemic_risk", strength=0.5, confidence=0.75, evidence_years=15),
    _e("india_10y", "systemic_risk", strength=0.48, confidence=0.74, evidence_years=12),
]
