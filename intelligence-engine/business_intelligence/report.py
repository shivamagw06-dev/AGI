"""Business Intelligence Report (BIR) assembly — sections 1–13."""

from __future__ import annotations

from typing import Any

from business_intelligence.engine import build_intelligence
from business_intelligence.schema import (
    CAPITAL_CATEGORIES,
    CAT_BUSINESS_DESCRIPTION,
    CAT_GEOGRAPHY,
    CAT_GOVERNANCE,
    CAT_OPERATING_MODEL,
    CAT_OPPORTUNITY,
    CAT_PRODUCTS,
    CAT_REVENUE_MODEL,
    CAT_RISK,
    CAT_SEGMENT_ANALYSIS,
    CAT_SEGMENTS,
    CAT_SERVICES,
    GUIDANCE_CATEGORIES,
    ISSUES_RECOMMENDATIONS,
    PACK_BUSINESS_PROFILE,
    PACK_CAPITAL_ALLOCATION,
    PACK_GUIDANCE_SUMMARY,
    PACK_MANAGEMENT_STRATEGY,
    PACK_OPPORTUNITY_REGISTER,
    PACK_RISK_REGISTER,
    PACK_SEGMENT_ANALYSIS,
    PROGRAMME,
    RECOMMENDATION_POLICY,
    REPORT_SECTIONS,
    SPEC,
    STRATEGY_CATEGORIES,
    VERSION,
    WORKSTREAM_ID,
)

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def _section(name: str, facts: list[dict[str, Any]], *, note: str | None = None) -> dict[str, Any]:
    return {
        "section": name,
        "n_facts": len(facts),
        "facts": facts,
        "statements": [f.get("statement") for f in facts if f.get("statement")],
        "note": note,
        # Explicit: BIR lists structured facts — it does not summarise with an LLM.
        "summarised": False,
        "uses_llm": False,
    }


def build_report(
    ticker: str,
    *,
    documents: list[dict[str, Any]] | None = None,
    pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    pack = pack or build_intelligence(ticker, documents=documents)
    facts: list[dict[str, Any]] = list(pack.get("facts") or [])
    packs = pack.get("packs") or {}

    profile = packs.get(PACK_BUSINESS_PROFILE) or [
        f for f in facts if f.get("category")
        in {
            CAT_BUSINESS_DESCRIPTION,
            CAT_PRODUCTS,
            CAT_SERVICES,
            CAT_OPERATING_MODEL,
            CAT_REVENUE_MODEL,
            CAT_SEGMENTS,
            CAT_GEOGRAPHY,
        }
    ]
    products = [f for f in facts if f.get("category") in {CAT_PRODUCTS, CAT_SERVICES}]
    revenue_model = [f for f in facts if f.get("category") == CAT_REVENUE_MODEL]
    segments = packs.get(PACK_SEGMENT_ANALYSIS) or [
        f for f in facts if f.get("category") in {CAT_SEGMENTS, CAT_SEGMENT_ANALYSIS}
    ]
    geo = [f for f in facts if f.get("category") == CAT_GEOGRAPHY]
    strategy = packs.get(PACK_MANAGEMENT_STRATEGY) or [
        f for f in facts if f.get("category") in STRATEGY_CATEGORIES
    ]
    capital = packs.get(PACK_CAPITAL_ALLOCATION) or [
        f for f in facts if f.get("category") in CAPITAL_CATEGORIES
    ]
    risks = packs.get(PACK_RISK_REGISTER) or [f for f in facts if f.get("category") == CAT_RISK]
    opps = packs.get(PACK_OPPORTUNITY_REGISTER) or [
        f for f in facts if f.get("category") == CAT_OPPORTUNITY
    ]
    guidance = packs.get(PACK_GUIDANCE_SUMMARY) or [
        f for f in facts if f.get("category") in GUIDANCE_CATEGORIES
    ]
    governance = [f for f in facts if f.get("category") == CAT_GOVERNANCE]
    sources = pack.get("sources") or []

    # Executive summary = top facts by confidence, not free-text narrative
    conf_rank = {"High": 0, "Medium": 1, "Low": 2}
    top = sorted(facts, key=lambda f: (conf_rank.get(str(f.get("confidence")), 9), f.get("category") or ""))[:8]

    sections: dict[str, Any] = {
        "executive_summary": _section(
            "executive_summary",
            top,
            note="Structured fact highlights from official disclosures — not an investment thesis.",
        ),
        "business_model": _section(
            "business_model",
            [f for f in profile if f.get("category") in {CAT_BUSINESS_DESCRIPTION, CAT_OPERATING_MODEL}],
        ),
        "products_and_services": _section("products_and_services", products),
        "revenue_model": _section("revenue_model", revenue_model),
        "segment_analysis": _section("segment_analysis", segments),
        "geographic_footprint": _section("geographic_footprint", geo),
        "management_strategy": _section("management_strategy", strategy),
        "capital_allocation": _section("capital_allocation", capital),
        "risk_register": _section(
            "risk_register",
            risks,
            note="Only risks disclosed by management; no inferred risks.",
        ),
        "opportunity_register": _section("opportunity_register", opps),
        "management_guidance": _section(
            "management_guidance",
            guidance,
            note="Only explicitly stated guidance / outlook language.",
        ),
        "governance_highlights": _section("governance_highlights", governance),
        "source_references": {
            "section": "source_references",
            "n_sources": len(sources),
            "sources": sources,
            "facts_with_page": sum(1 for f in facts if f.get("page") is not None),
            "facts_with_section": sum(1 for f in facts if f.get("section")),
            "summarised": False,
            "uses_llm": False,
        },
    }

    # Ensure all declared sections present
    for name in REPORT_SECTIONS:
        sections.setdefault(name, _section(name, []))

    return {
        "ok": True,
        "workstream_id": WORKSTREAM_ID,
        "programme": PROGRAMME,
        "version": VERSION,
        "ticker": pack.get("ticker"),
        "report_type": "BusinessIntelligenceReport",
        "report_code": "BIR",
        "sections": sections,
        "facts": facts,
        "packs": {
            PACK_BUSINESS_PROFILE: packs.get(PACK_BUSINESS_PROFILE) or profile,
            PACK_MANAGEMENT_STRATEGY: strategy,
            PACK_SEGMENT_ANALYSIS: segments,
            PACK_RISK_REGISTER: risks,
            PACK_OPPORTUNITY_REGISTER: opps,
            PACK_GUIDANCE_SUMMARY: guidance,
            PACK_CAPITAL_ALLOCATION: capital,
        },
        "BusinessProfile": packs.get(PACK_BUSINESS_PROFILE) or profile,
        "ManagementStrategy": strategy,
        "SegmentAnalysis": segments,
        "RiskRegister": risks,
        "OpportunityRegister": opps,
        "GuidanceSummary": guidance,
        "CapitalAllocationNarrative": capital,
        "mission_control": pack.get("mission_control") or {},
        "sources": sources,
        "confidence": {
            "distribution": (pack.get("mission_control") or {}).get("confidence_distribution"),
        },
        "issues_recommendations": ISSUES_RECOMMENDATIONS,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "buy_sell": False,
        "forecast": False,
        "uses_llm": False,
        "fire_01_unchanged": True,
        "fire_02_unchanged": True,
        "spec": SPEC,
        "as_of": now_iso(),
        "inventory_notes": pack.get("inventory_notes") or [],
    }
