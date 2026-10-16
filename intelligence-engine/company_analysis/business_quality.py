"""Step 6 — Business quality score from moat / management / capital allocation signals."""

from __future__ import annotations

from typing import Any

from company_analysis.flags import flag_business


def score_business_quality(
    *,
    identity: dict[str, Any],
    academy_applied: dict[str, Any] | None = None,
    financial: dict[str, Any] | None = None,
    sif_pkg: dict[str, Any] | None = None,
    cid: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not flag_business():
        return {"enabled": False, "bypassed": True}

    applied = list((academy_applied or {}).get("applied_concepts") or [])
    titles = " ".join(str(c.get("title") or "") for c in applied).lower()
    fin = financial or {}
    sk = str(identity.get("sector_id") or identity.get("sector") or "").lower()

    dimensions = {
        "competitive_advantage": 55,
        "management_quality": 50,
        "capital_allocation": 50,
        "industry_position": 55,
        "brand_strength": 50,
        "customer_relationships": 50,
        "supplier_dependence": 50,
        "switching_costs": 45,
        "scale": 55,
        "network_effects": 35,
        "economic_moat": 55,
    }

    if "moat" in titles or "advantage" in titles:
        dimensions["competitive_advantage"] += 15
        dimensions["economic_moat"] += 15
    if "brand" in titles or "pricing" in titles:
        dimensions["brand_strength"] += 20
        dimensions["pricing_power"] = 70
    if "capital allocation" in titles or "roic" in titles or "roe" in titles:
        dimensions["capital_allocation"] += 15
    if fin.get("returns") is not None:
        dimensions["capital_allocation"] += 5
        dimensions["economic_moat"] += 5
    if identity.get("business_model"):
        dimensions["industry_position"] += 5
    if "bank" in sk:
        dimensions["switching_costs"] += 10
        dimensions["scale"] += 10
        dimensions["network_effects"] += 15  # payments / deposit franchise
        dimensions["brand_strength"] += 5
    if "fmcg" in sk or "staple" in sk:
        dimensions["brand_strength"] += 15
        dimensions["customer_relationships"] += 10
        dimensions["switching_costs"] += 5

    # Clamp
    for k, v in list(dimensions.items()):
        dimensions[k] = max(0, min(100, int(v)))

    score = int(round(sum(dimensions.values()) / max(1, len(dimensions))))
    grade = "A" if score >= 80 else "B" if score >= 65 else "C" if score >= 50 else "D"

    evidence = []
    for c in applied[:6]:
        evidence.append(
            {
                "claim": c.get("application"),
                "source": "academy",
                "concept": c.get("title"),
            }
        )
    if identity.get("business_model"):
        evidence.append({"claim": identity["business_model"], "source": "identity", "concept": "business_model"})

    return {
        "enabled": True,
        "business_quality_score": score,
        "grade": grade,
        "dimensions": dimensions,
        "summary": f"Business quality score {score}/100 (grade {grade}) for {identity.get('ticker')}.",
        "evidence": evidence,
        "coverage_pct": min(100, 40 + len(applied) * 5 + (10 if identity.get("business_model") else 0)),
        "sources": ["academy.applied_concepts", "identity", "sif", "financial_intelligence"],
    }
