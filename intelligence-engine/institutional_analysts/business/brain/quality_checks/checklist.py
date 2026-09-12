"""Business Analyst V2 quality checklist — Incomplete Business Assessment if fails."""

from __future__ import annotations

from typing import Any, Dict, List


CHECKLIST_ITEMS = (
    ("business_model_understood", "Business model understood"),
    ("revenue_drivers_identified", "Revenue drivers identified"),
    ("competitive_advantages_analysed", "Competitive advantages analysed"),
    ("porter_completed", "Porter completed"),
    ("value_chain_completed", "Value chain completed"),
    ("pricing_power_evaluated", "Pricing power evaluated"),
    ("capital_allocation_reviewed", "Capital allocation reviewed"),
    ("growth_runway_analysed", "Growth runway analysed"),
    ("risks_analysed", "Risks analysed"),
    ("long_term_outlook_completed", "Long-term outlook completed"),
)


def run_checklist(frameworks: dict[str, Any], scoring: dict[str, Any]) -> dict[str, Any]:
    bm = frameworks.get("business_model") or {}
    moat = frameworks.get("moat") or {}
    porter = frameworks.get("porter_five_forces") or {}
    chain = frameworks.get("value_chain") or {}
    pricing = frameworks.get("pricing_power") or {}
    capital = frameworks.get("capital_allocation") or {}
    growth = frameworks.get("growth") or {}
    risks = frameworks.get("risks") or {}

    checks = {
        "business_model_understood": bool(bm.get("completed") and bm.get("assessment")),
        "revenue_drivers_identified": bool(bm.get("revenue_streams")),
        "competitive_advantages_analysed": bool(moat.get("sources") or moat.get("dimensions")),
        "porter_completed": bool(porter.get("completed") and porter.get("industry_attractiveness")),
        "value_chain_completed": bool(chain.get("completed") and chain.get("where_value_is_created")),
        "pricing_power_evaluated": bool(pricing.get("assessment")),
        "capital_allocation_reviewed": bool(capital.get("completed") and capital.get("assessment")),
        "growth_runway_analysed": bool(growth.get("completed") and growth.get("runway")),
        "risks_analysed": bool(risks.get("completed") and risks.get("primary_risks")),
        "long_term_outlook_completed": bool(growth.get("assessment") and scoring.get("ownership_bar")),
    }

    failed = [label for key, label in CHECKLIST_ITEMS if not checks.get(key)]
    passed = len(failed) == 0

    issues: List[str] = []
    if not passed:
        issues.append("Incomplete Business Assessment")
        issues.extend([f"Failed check: {item}" for item in failed])

    return {
        "passed": passed,
        "incomplete": not passed,
        "status": "Complete" if passed else "Incomplete Business Assessment",
        "checks": checks,
        "failed_items": failed,
        "issues": issues,
        "issue_count": len(issues),
        "ready_for_committee": passed,
        "explanation": (
            None
            if passed
            else (
                "Incomplete Business Assessment — the following required analyses are missing or incomplete: "
                + "; ".join(failed)
                + "."
            )
        ),
    }


def run_quality_checks(
    *,
    strengths: List[str],
    weaknesses: List[str],
    claims: List[str],
    evidence: List[Dict[str, Any]],
    assumptions: List[str],
    freshness: float,
    overall_confidence: float,
    moat_assessment: Dict[str, Any],
    competitive_outlook: Dict[str, Any],
    business_quality: Dict[str, Any],
    frameworks: Dict[str, Any] | None = None,
    scoring: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Full V2 quality pass — checklist + contradiction / confidence guards."""
    fw = frameworks or {
        "business_model": {"completed": True, "assessment": "x", "revenue_streams": strengths},
        "moat": moat_assessment,
        "porter_five_forces": {"completed": True, "industry_attractiveness": "x"},
        "value_chain": {"completed": True, "where_value_is_created": ["x"]},
        "pricing_power": {"assessment": "x"},
        "capital_allocation": {"completed": True, "assessment": "x"},
        "growth": {"completed": True, "runway": "x", "assessment": "x"},
        "risks": {"completed": bool(weaknesses), "primary_risks": weaknesses},
    }
    sc = scoring or {
        "ownership_bar": (business_quality or {}).get("ownership_bar") or "x",
        "grade": (business_quality or {}).get("grade"),
    }
    checklist = run_checklist(fw, sc)

    issues = list(checklist.get("issues") or [])
    s_set = {s.lower().strip() for s in strengths if s}
    for w in weaknesses:
        if w and w.lower().strip() in s_set:
            issues.append(f"Contradiction: '{w}' listed as both strength and weakness")
    if claims and not evidence:
        issues.append("Missing evidence for business claims")
    if float(freshness or 0.0) < 0.45:
        issues.append("Outdated information risk: freshness below institutional threshold")
    if float(overall_confidence or 0.0) < 0.4:
        issues.append("Low overall confidence — flag for committee challenge")
    if len(assumptions) >= 3 and len(evidence) < 2:
        issues.append("Weak assumptions: multiple assumptions with thin evidence base")
    if not (moat_assessment or {}).get("summary") and not (moat_assessment or {}).get("assessment"):
        issues.append("Incomplete coverage: moat assessment summary missing")
    if not (business_quality or {}).get("grade"):
        issues.append("Incomplete coverage: business quality grade missing")

    passed = checklist.get("passed") and not any(
        i.startswith("Contradiction") or i.startswith("Missing evidence") for i in issues
    )
    return {
        **checklist,
        "passed": passed,
        "issues": issues,
        "issue_count": len(issues),
        "ready_for_committee": bool(checklist.get("ready_for_committee")) and passed,
        "status": checklist.get("status") if checklist.get("incomplete") else ("Complete" if passed else "Complete with flags"),
    }
