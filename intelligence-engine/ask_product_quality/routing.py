"""Intent → entity → domain → required intelligence → provider ranking.

AQE does not replace KUL/UKO planners — it inspects and scores their plans
so admin dashboards and regression can track routing quality.
"""

from __future__ import annotations

from typing import Any, Optional

# Canonical Ask domains for institutional routing quality.
DOMAINS = (
    "company_analysis",
    "valuation",
    "macro",
    "comparison",
    "forecast",
    "historical",
    "hedge_fund",
    "educational",
    "metadata",
    "unknown",
)

_DOMAIN_FROM_FAMILY = {
    "valuation": "valuation",
    "attribution": "valuation",
    "historical": "historical",
    "forecast": "forecast",
    "macro": "macro",
    "market": "macro",
    "comparison": "comparison",
    "screen": "hedge_fund",
    "company_intel": "company_analysis",
    "investment": "company_analysis",
    "business": "company_analysis",
    "industry": "educational",
    "concept": "educational",
    "research": "company_analysis",
    "metadata": "metadata",
}


def classify_domain(question: str, *, family: Optional[str] = None, types: Optional[list[str]] = None) -> str:
    """Map planner family / question types onto an AQE domain."""
    if family and family in _DOMAIN_FROM_FAMILY:
        return _DOMAIN_FROM_FAMILY[family]
    tset = set(types or [])
    if "comparison" in tset:
        return "comparison"
    if "attribution" in tset or "valuation" in tset:
        return "valuation"
    if "historical" in tset:
        return "historical"
    if "forecast" in tset:
        return "forecast"
    if "macro" in tset or "market_summary" in tset:
        return "macro"
    if "screen" in tset:
        return "hedge_fund"
    if tset.intersection({"concept", "accounting", "financial_statement", "industry"}):
        return "educational"
    if tset.intersection({"business_model", "moat", "company", "investment", "research"}):
        return "company_analysis"
    q = (question or "").lower()
    if any(k in q for k in ("compare", " vs ", "versus")):
        return "comparison"
    if any(k in q for k in ("what is", "explain", "define")):
        return "educational"
    return "unknown"


def inspect_routing(question: str, *, ticker: Optional[str] = None) -> dict[str, Any]:
    """Run planners and return a structured routing inspection (no vendors)."""
    from knowledge_unification.query_planner import plan_query
    from knowledge_unification.knowledge_planner import build_knowledge_plan

    query = plan_query(question)
    if ticker and not query.ticker_hint:
        query.ticker_hint = str(ticker).upper()
    plan = build_knowledge_plan(query)
    family = None
    try:
        from universal_knowledge.planner import detect_family

        family = detect_family(question, question_type=(query.question_types or [None])[0])
    except Exception:
        family = (query.question_types or ["unknown"])[0]

    domain = classify_domain(question, family=family, types=list(query.question_types or []))
    ei: dict[str, Any] = {}
    try:
        from entity_intelligence.production import analyse

        ei = analyse(question) or {}
    except Exception as exc:
        ei = {"error": str(exc)}

    meta = None
    try:
        from company_identity.metadata_router import route as metadata_route

        meta = metadata_route(question)
    except Exception:
        meta = None

    return {
        "question": question,
        "domain": domain if not meta else "metadata",
        "family": "metadata" if meta else family,
        "question_types": list(query.question_types or []),
        "entity": {
            "state": ei.get("state"),
            "ticker": ei.get("ticker"),
            "canonical_name": ei.get("canonical_name"),
            "confidence": ei.get("confidence"),
            "allow_planner": ei.get("allow_planner"),
            "pedagogy_only": bool(ei.get("pedagogy_only")),
        },
        "provider_ids": list(plan.provider_ids or []),
        "rationale": list(plan.rationale or []),
        "metadata_route": bool(meta),
        "required_intelligence": _required_intelligence(domain if not meta else "metadata"),
    }


def _required_intelligence(domain: str) -> list[str]:
    return {
        "company_analysis": ["business_intelligence", "capiq_ikt", "research_intelligence_engine"],
        "valuation": ["unified_valuation_engine", "historical_valuation_intelligence", "valuation_attribution_engine"],
        "macro": ["macro_intelligence_engine", "market_intelligence_engine"],
        "comparison": ["business_intelligence", "capiq_ikt", "industry_intelligence"],
        "forecast": ["forecast_intelligence_engine", "research_intelligence_engine"],
        "historical": ["historical_valuation_intelligence", "unified_valuation_engine"],
        "hedge_fund": ["hedge_fund_screens", "unified_valuation_engine"],
        "educational": ["financial_concepts", "financial_foundations", "industry_intelligence"],
        "metadata": ["company_identity"],
        "unknown": ["financial_concepts"],
    }.get(domain, ["financial_concepts"])


def routing_accuracy(inspections: list[dict[str, Any]]) -> dict[str, Any]:
    """Score whether selected providers cover required intelligence."""
    if not inspections:
        return {"total": 0, "hits": 0, "accuracy_pct": 0.0}
    hits = 0
    for row in inspections:
        required = set(row.get("required_intelligence") or [])
        selected = set(row.get("provider_ids") or [])
        if row.get("metadata_route"):
            hits += 1
            continue
        if required and required.intersection(selected):
            hits += 1
        elif not required:
            hits += 1
    total = len(inspections)
    return {
        "total": total,
        "hits": hits,
        "accuracy_pct": round(100.0 * hits / total, 2) if total else 0.0,
    }
