"""Business Analyst V2 structured opinion templates."""

from __future__ import annotations

from typing import Any, Dict, List


def structured_business_opinion_template() -> Dict[str, Any]:
    return {
        "executive_opinion": "",
        "business_quality": {},
        "moat": {},
        "competitive_position": "",
        "business_model": {},
        "revenue_drivers": [],
        "customer_economics": {},
        "pricing_power": {},
        "capital_allocation": {},
        "innovation": "",
        "industry_position": "",
        "growth_runway": "",
        "risks": [],
        "opportunities": [],
        "assumptions": [],
        "uncertainties": [],
        "missing_evidence": [],
        "confidence": {
            "evidence": 0.0,
            "reasoning": 0.0,
            "knowledge": 0.0,
            "freshness": 0.0,
            "overall": 0.0,
        },
        "quality_checks": {},
    }


def build_structured_opinion(
    *,
    executive_opinion: str,
    business_quality: Dict[str, Any],
    moat: Dict[str, Any],
    competitive_position: str,
    business_model: Dict[str, Any],
    revenue_drivers: List[str],
    customer_economics: Dict[str, Any],
    pricing_power: Dict[str, Any],
    capital_allocation: Dict[str, Any],
    innovation: str,
    industry_position: str,
    growth_runway: str,
    risks: List[str],
    opportunities: List[str],
    assumptions: List[str],
    uncertainties: List[str],
    missing_evidence: List[str],
    confidence: Dict[str, float],
    quality_checks: Dict[str, Any],
) -> Dict[str, Any]:
    out = structured_business_opinion_template()
    out.update(
        {
            "executive_opinion": executive_opinion,
            "business_quality": business_quality,
            "moat": moat,
            "competitive_position": competitive_position,
            "business_model": business_model,
            "revenue_drivers": revenue_drivers,
            "customer_economics": customer_economics,
            "pricing_power": pricing_power,
            "capital_allocation": capital_allocation,
            "innovation": innovation,
            "industry_position": industry_position,
            "growth_runway": growth_runway,
            "risks": risks,
            "opportunities": opportunities,
            "assumptions": assumptions,
            "uncertainties": uncertainties,
            "missing_evidence": missing_evidence,
            "confidence": confidence,
            "quality_checks": quality_checks,
        }
    )
    return out


def render_opinion_prose(
    *,
    company: str,
    stance: str,
    business_quality: Dict[str, Any],
    moat_assessment: Dict[str, Any],
    competitive_outlook: Dict[str, Any] | str | None = None,
    strengths: List[str] | None = None,
    weaknesses: List[str] | None = None,
    executive_opinion: str | None = None,
) -> str:
    if executive_opinion:
        return str(executive_opinion)
    _ = company, stance, business_quality, moat_assessment, competitive_outlook, strengths, weaknesses
    return str((moat_assessment or {}).get("assessment") or "")
