"""Framework 12 — Business quality dimensions (never expose calculation publicly)."""

from __future__ import annotations

from typing import Any


def _band(value: float) -> str:
    if value >= 0.8:
        return "Exceptional"
    if value >= 0.65:
        return "High"
    if value >= 0.5:
        return "Adequate"
    return "Weak"


def score_dimensions(frameworks: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    moat = frameworks.get("moat") or {}
    capital = frameworks.get("capital_allocation") or {}
    growth = frameworks.get("growth") or {}
    mgmt = frameworks.get("management") or {}
    pricing = frameworks.get("pricing_power") or {}
    risks = frameworks.get("risks") or {}
    porter = frameworks.get("porter_five_forces") or {}

    durability = str(moat.get("durability") or "Weak")
    moat_n = {"Strong": 0.9, "Improving": 0.8, "Medium": 0.62, "Weak": 0.35, "Declining": 0.25}.get(
        durability, 0.5
    )

    biz_score = evidence.get("business_quality_score")
    try:
        base = float(biz_score) / 100.0 if biz_score is not None else None
    except Exception:
        base = None

    management_n = 0.7 if mgmt.get("completed") and "discipline" in str(mgmt.get("assessment") or "").lower() else 0.55
    capital_n = 0.75 if capital.get("completed") else 0.5
    growth_n = 0.72 if growth.get("completed") and (growth.get("growth_drivers") or []) else 0.48
    innovation_n = 0.65 if "technology" in str((growth.get("technology") or "")).lower() and "enabler" not in str(growth.get("technology") or "").lower() else 0.5
    resilience_n = 0.7 if "Attractive" in str(porter.get("industry_attractiveness") or "") else 0.55
    if len(list(risks.get("primary_risks") or [])) >= 4:
        resilience_n -= 0.1
    execution_n = management_n
    if pricing.get("can_raise_prices"):
        moat_n = min(0.95, moat_n + 0.05)

    if base is not None:
        business_quality_n = max(0.2, min(0.95, 0.55 * base + 0.45 * moat_n))
    else:
        business_quality_n = moat_n

    dims = {
        "business_quality": _band(business_quality_n),
        "moat": _band(moat_n),
        "management": _band(management_n),
        "capital_allocation": _band(capital_n),
        "growth": _band(growth_n),
        "resilience": _band(resilience_n),
        "innovation": _band(innovation_n),
        "execution": _band(execution_n),
    }

    # Internal only — not for user-facing copy
    internal = {
        "business_quality": round(business_quality_n, 4),
        "moat": round(moat_n, 4),
        "management": round(management_n, 4),
        "capital_allocation": round(capital_n, 4),
        "growth": round(growth_n, 4),
        "resilience": round(resilience_n, 4),
        "innovation": round(innovation_n, 4),
        "execution": round(execution_n, 4),
    }
    overall_n = round(sum(internal.values()) / len(internal), 4)

    grade = _band(overall_n)
    exceptional = grade == "Exceptional" or (
        dims["moat"] in {"Exceptional", "High"} and dims["business_quality"] in {"Exceptional", "High"}
    )

    return {
        "framework": "Quality Score",
        "dimensions": dims,
        "grade": grade,
        "exceptional_business": exceptional,
        "ownership_bar": (
            "Clears the bar as an exceptional / high-quality long-term ownership candidate on business grounds"
            if exceptional or grade in {"Exceptional", "High"}
            else "Does not yet clear the exceptional-business bar on present evidence"
            if grade == "Weak"
            else "Credible franchise; not yet exceptional without fuller confirmation"
        ),
        # Keep numeric internals out of public templates
        "_internal": {"dimension_scores": internal, "overall": overall_n},
    }
