"""Freshness engine — required freshness by question type."""

from __future__ import annotations

from typing import Any

FRESHNESS_BY_OBJECTIVE: dict[str, dict[str, Any]] = {
    "fact_retrieval": {"required": "live", "max_age_hours": 0.25, "label": "Live / intraday"},
    "monitoring_update": {"required": "intraday", "max_age_hours": 4, "label": "Intraday"},
    "valuation_assessment": {"required": "daily", "max_age_hours": 24, "label": "Daily acceptable"},
    "decision_support": {"required": "daily", "max_age_hours": 24, "label": "Daily acceptable"},
    "opportunity_assessment": {"required": "daily", "max_age_hours": 24, "label": "Daily acceptable"},
    "comparison_assessment": {"required": "daily", "max_age_hours": 48, "label": "Daily / short stale OK"},
    "forecast_assessment": {"required": "quarterly", "max_age_hours": 24 * 45, "label": "Quarterly acceptable"},
    "risk_assessment": {"required": "daily", "max_age_hours": 24, "label": "Daily acceptable"},
    "portfolio_assessment": {"required": "intraday", "max_age_hours": 8, "label": "Intraday"},
    "educational_explanation": {"required": "existing_knowledge", "max_age_hours": 24 * 365, "label": "Existing knowledge OK"},
}

FRESHNESS_BY_EVIDENCE: dict[str, str] = {
    "live_prices": "live",
    "press_flow": "intraday",
    "quarterly_results": "quarterly",
    "official_filings": "quarterly",
    "historical_valuation": "daily",
    "historical_financials": "quarterly",
    "macro_data": "daily",
    "management_commentary": "quarterly",
    "peer_metrics": "daily",
    "portfolio_exposure": "intraday",
    "knowledge_graph_context": "existing_knowledge",
    "evidence_corpus": "existing_knowledge",
    "regulatory_policy": "daily",
}


def resolve_freshness_plan(
    *,
    primary_objective: str | None = None,
    required_data: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    obj = (primary_objective or "decision_support").strip().lower()
    base = dict(FRESHNESS_BY_OBJECTIVE.get(obj, FRESHNESS_BY_OBJECTIVE["decision_support"]))
    per_evidence = []
    for item in required_data or []:
        key = str(item.get("evidence_key") or "")
        per_evidence.append(
            {
                "evidence_key": key,
                "required_freshness": FRESHNESS_BY_EVIDENCE.get(key, base["required"]),
            }
        )
    return {
        "objective_freshness": base,
        "per_evidence": per_evidence,
        "required_freshness": base["required"],
        "max_age_hours": base["max_age_hours"],
    }
