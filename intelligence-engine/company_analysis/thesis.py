"""Step 7 — Investment thesis / bull / base / bear (evidence-framed; never a buy call)."""

from __future__ import annotations

from typing import Any

from company_analysis.flags import flag_investment_thesis


def build_thesis(
    *,
    identity: dict[str, Any],
    academy_applied: dict[str, Any] | None = None,
    financial: dict[str, Any] | None = None,
    valuation: dict[str, Any] | None = None,
    sector: dict[str, Any] | None = None,
    business_quality: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not flag_investment_thesis():
        return {"enabled": False, "bypassed": True}

    t = identity.get("ticker") or "Company"
    name = identity.get("company_name") or t
    sk = str(identity.get("sector_id") or identity.get("sector") or "sector")
    bq = (business_quality or {}).get("business_quality_score")
    apps = list((academy_applied or {}).get("applied_concepts") or [])[:5]
    app_titles = ", ".join(c.get("title") for c in apps if c.get("title")) or "core Academy concepts"

    overview = identity.get("business_model") or f"{name} ({t}) operates in {sk}."
    thesis = (
        f"{name} should be analysed as a {sk} franchise. Key applied lenses: {app_titles}. "
        f"Business quality score: {bq if bq is not None else 'n/a'}. "
        "This is an institutional analysis frame — not a recommendation."
    )

    if "bank" in sk.lower():
        bull = (
            "Funding advantage (CASA) sustains NIM, credit costs stay benign, and ROE compounds "
            "without excessive leverage — supporting a quality premium if valuation is reasonable."
        )
        bear = (
            "Liability costs rise, credit costs normalise higher, and growth slows — compressing ROE "
            "and de-rating P/B if capital or asset quality weakens."
        )
        base = (
            "Franchise remains intact with mid-cycle credit costs; returns stay adequate while "
            "valuation tracks historical relationship to ROE/growth."
        )
        catalysts = ["Stable/improving CASA", "Benign credit cost prints", "Loan growth with capital headroom"]
        risks = ["Rate-cycle NIM squeeze", "Asset-quality surprise", "Regulatory capital drag", "Funding mix deterioration"]
    elif "fmcg" in sk.lower() or "staple" in sk.lower():
        bull = (
            "Pricing power + distribution deepen moat; ROIC stays high with strong cash conversion — "
            "justifying premium multiples if volume re-accelerates."
        )
        bear = (
            "Volume weakness, competitive pricing, or WC/cash conversion deterioration undermines "
            "the quality premium."
        )
        base = "Steady mid-single-digit volume with pricing offsets; ROIC durable; valuation near history."
        catalysts = ["Volume recovery", "Gross margin defence", "Distribution gains"]
        risks = ["Input cost inflation", "Downtrading", "Regulatory / product issues", "Premium compression"]
    else:
        bull = f"Operating trends improve and returns expand while valuation stays reasonable for {t}."
        bear = f"Growth/margins disappoint or balance-sheet risk rises, forcing multiple compression for {t}."
        base = f"Franchise executes in line with sector mid-cycle assumptions for {t}."
        catalysts = list((sector or {}).get("priority_metrics") or [])[:3] or ["Earnings delivery", "Margin stability"]
        risks = list((financial or {}).get("what_deserves_monitoring") or [])[:4] or ["Execution", "Cyclicality", "Valuation"]

    industry_drivers = list((sector or {}).get("priority_metrics") or [])[:6]
    macro_drivers = ["Rates / liquidity", "Growth cycle", "Inflation / input costs", "Regulatory stance"]
    if "bank" in sk.lower():
        macro_drivers = ["Policy rates", "Credit cycle", "Liquidity", "Regulatory capital"]

    return {
        "enabled": True,
        "business_overview": overview,
        "investment_thesis": thesis,
        "bull_case": bull,
        "bear_case": bear,
        "base_case": base,
        "catalysts": catalysts,
        "risks": risks,
        "industry_drivers": industry_drivers,
        "macro_drivers": macro_drivers,
        "valuation_discussion": (valuation or {}).get("narrative"),
        "financial_discussion": (financial or {}).get("narrative"),
        "historical_evolution": (
            "Compare current returns, margins and valuation to dossier history and prior research — "
            "see what_changed for deltas."
        ),
        "not_a_recommendation": True,
        "sources": ["academy", "sector", "financial_intelligence", "valuation_intelligence", "business_quality"],
    }
