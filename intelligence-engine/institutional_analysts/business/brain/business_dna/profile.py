"""Business DNA — durable company fingerprint updated each review."""

from __future__ import annotations

from typing import Any

from institutional_analysts.business.brain._text import as_list, blob_of, txt


def build_dna(
    *,
    company: str,
    ticker: str | None,
    evidence: dict[str, Any],
    frameworks: dict[str, Any],
    scoring: dict[str, Any],
    prior_dna: dict[str, Any] | None = None,
) -> dict[str, Any]:
    moat = frameworks.get("moat") or {}
    bm = frameworks.get("business_model") or {}
    pricing = frameworks.get("pricing_power") or {}
    customers = frameworks.get("customer_economics") or {}
    growth = frameworks.get("growth") or {}
    capital = frameworks.get("capital_allocation") or {}
    dims = (scoring.get("dimensions") or {}) if isinstance(scoring, dict) else {}

    blob = blob_of(
        evidence.get("business_model"),
        evidence.get("advantages"),
        evidence.get("pricing_power"),
        evidence.get("capital_allocation"),
        moat.get("sources"),
    )

    dna = {
        "company": company,
        "ticker": (ticker or "").upper() or None,
        "revenue_model": bm.get("platform_vs_product") or txt(evidence.get("business_model")) or "Franchise / product mix",
        "capital_intensity": bm.get("asset_intensity") or "Mixed capital intensity",
        "pricing_power": (
            "High"
            if pricing.get("can_raise_prices")
            else dims.get("moat")
            if dims.get("moat") in {"High", "Exceptional"}
            else "Medium"
            if pricing.get("assessment")
            else "Low"
        ),
        "customer_stickiness": (
            "High"
            if any(k in blob for k in ("switch", "retention", "franchise", "ecosystem", "casa", "trust"))
            else "Medium"
        ),
        "innovation": dims.get("innovation") or ("Medium" if "tech" in blob or "digital" in blob else "Low"),
        "moat": moat.get("durability") or dims.get("moat") or "Medium",
        "growth": dims.get("growth") or ("High" if growth.get("growth_drivers") else "Medium"),
        "cash_generation": (
            "High"
            if "cash" in str(bm.get("cash_generation") or "").lower()
            or any(k in blob for k in ("deposit", "fee", "franchise", "staples"))
            else "Medium"
        ),
        "scalability": (
            "High"
            if any(k in blob for k in ("scale", "network", "platform", "distribution"))
            else "Medium"
        ),
        "risk_profile": (
            "Elevated"
            if len(as_list(evidence.get("business_risks"), limit=6)) >= 4
            else "Moderate"
        ),
        "archetype": None,  # filled by caller
        "quality_grade": scoring.get("grade"),
        "updated_from_prior": bool(prior_dna),
    }

    changes: list[str] = []
    if prior_dna:
        for key in (
            "pricing_power",
            "customer_stickiness",
            "moat",
            "growth",
            "cash_generation",
            "scalability",
            "risk_profile",
            "quality_grade",
        ):
            old = prior_dna.get(key)
            new = dna.get(key)
            if old and new and str(old) != str(new):
                changes.append(f"{key}: {old} → {new}")

    dna["dna_changes"] = changes[:8]
    dna["summary"] = (
        f"{company} DNA — moat {dna['moat']}, pricing power {dna['pricing_power']}, "
        f"stickiness {dna['customer_stickiness']}, cash generation {dna['cash_generation']}, "
        f"scalability {dna['scalability']}, risk {dna['risk_profile']}."
    )
    return dna
