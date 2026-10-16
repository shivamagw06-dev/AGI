"""Evidence quality gates — withhold institutional recommendations when evidence is thin."""

from __future__ import annotations

from typing import Any

from leo.schema import LEO_TO_SIF_EVIDENCE


CORE_INVESTMENT_TYPES = (
    "annual_report",
    "quarterly_results",
    "financial_statements",
    "market_data",
    "corporate_announcement",
    "sector_kpis",
    "valuation_metrics",
)

# Must-have subset for any institutional Buy/Hold/Sell (mission completion bar)
MUST_HAVE_INVESTMENT = (
    "annual_report",
    "quarterly_results",
    "financial_statements",
    "market_data",
    "corporate_announcement",
    "sector_kpis",
    "valuation_metrics",
)


def assess_quality_gate(
    plan: dict[str, Any],
    evidence_objects: list[dict[str, Any]],
    usage: dict[str, Any],
) -> dict[str, Any]:
    present_types = {o.get("evidence_type") for o in evidence_objects or []}
    required = list(plan.get("required_evidence") or [])
    present_required = [t for t in required if t in present_types]
    missing = [t for t in required if t not in present_types]

    # Soft: optional types that remain missing
    optional_missing = [t for t in (plan.get("optional_evidence") or []) if t not in present_types]

    core_present = [t for t in CORE_INVESTMENT_TYPES if t in present_types]
    must_missing = [t for t in MUST_HAVE_INVESTMENT if t not in present_types]
    intent = plan.get("intent") or "general_finance"
    is_investment = intent == "investment_recommendation"

    has_external = bool(usage.get("external_api_contributed"))
    has_document = bool(usage.get("documents_used"))
    has_objects = bool(evidence_objects)

    # Investment bar: every must-have type + external/corporate contribution + objects
    core_ok = not must_missing
    allow = (not is_investment) or (core_ok and has_objects and (has_external or has_document))

    message = None
    if is_investment and not allow:
        message = (
            "Institutional recommendation withheld due to insufficient current evidence. "
            "LEO requires latest filings, market data, announcements, sector KPIs and valuation inputs "
            "from verified external sources before Buy/Hold/Sell."
        )

    sif_supplied = {}
    for leo_t, sif_t in LEO_TO_SIF_EVIDENCE.items():
        if leo_t in present_types:
            sif_supplied[sif_t] = True

    return {
        "allow_recommendation": allow,
        "blocked": is_investment and not allow,
        "intent": intent,
        "is_investment": is_investment,
        "present_types": sorted(present_types),
        "present_required": present_required,
        "missing_evidence": missing,
        "optional_missing": optional_missing,
        "core_present": core_present,
        "must_have_missing": must_missing,
        "has_external_contribution": has_external,
        "has_company_document": has_document,
        "evidence_object_count": len(evidence_objects or []),
        "sif_evidence_supplied": sif_supplied,
        "message": message,
        "policy": "verified_live_evidence_before_recommendation",
    }


def quality_gates_report(sample_packages: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate gate checks for admin / CI."""
    rows = []
    for pkg in sample_packages:
        gate = pkg.get("quality_gate") or {}
        rows.append(
            {
                "ticker": pkg.get("ticker"),
                "intent": pkg.get("intent"),
                "external": (pkg.get("usage") or {}).get("external_api_contributed"),
                "objects": len(pkg.get("evidence_objects") or []),
                "blocked": gate.get("blocked"),
                "missing": gate.get("missing_evidence") or [],
            }
        )
    return {
        "checks": rows,
        "pass": all(r.get("objects", 0) > 0 for r in rows) if rows else False,
        "external_contribution_rate": (
            sum(1 for r in rows if r.get("external")) / len(rows) if rows else 0.0
        ),
    }
