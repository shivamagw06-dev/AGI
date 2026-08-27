"""IDS-01 decision validator — reject impossible / incomplete decisions."""

from __future__ import annotations

from institutional_decision.models import DecisionValidationResult, InstitutionalDecision
from institutional_decision.recommendation_rules import business_quality_band_safe
from institutional_decision.schema import CONVICTIONS, HORIZONS, RECOMMENDATIONS


def validate_decision(
    decision: InstitutionalDecision,
    *,
    business_quality: object = None,
    valuation: str = "",
    overall_risk: str = "",
) -> DecisionValidationResult:
    errors: list[str] = []

    if not decision.ticker:
        errors.append("ticker is required")
    if not decision.decision_id:
        errors.append("decision_id is required")
    if int(decision.decision_version or 0) < 1:
        errors.append("decision_version must be >= 1")
    if not decision.generated_at:
        errors.append("generated_at is required")
    if not decision.evidence_snapshot_id:
        errors.append("evidence_snapshot_id is required")

    rec = str(decision.recommendation or "").strip().upper()
    conv = str(decision.conviction or "").strip().upper()
    if rec not in RECOMMENDATIONS:
        errors.append(f"recommendation must be one of {list(RECOMMENDATIONS)}")
    if conv not in CONVICTIONS:
        errors.append(f"conviction must be one of {list(CONVICTIONS)}")

    if rec == "BUY" and conv == "LOW":
        errors.append("impossible combination: BUY with LOW conviction")
    if rec == "SELL" and conv == "LOW":
        errors.append("impossible combination: SELL with LOW conviction")

    # Optional contextual contradiction when caller supplies factor snapshot
    bq = business_quality_band_safe(business_quality) if business_quality is not None else ""
    val = str(valuation or "").strip().title()
    risk = str(overall_risk or "").strip().title()
    if rec == "SELL" and bq == "Excellent" and val == "Cheap" and risk == "Low":
        errors.append(
            "impossible combination: SELL with Excellent business quality, Cheap valuation, Low risk"
        )

    if not isinstance(decision.confidence, int) or decision.confidence < 0 or decision.confidence > 100:
        errors.append("confidence must be an integer between 0 and 100")

    horizon = str(decision.investment_horizon or "").strip()
    if horizon not in HORIZONS:
        errors.append(f"investment_horizon must be one of {list(HORIZONS)}")

    if not decision.evidence_ids or decision.evidence_ids == ("EVIDENCE-REQUIRED",):
        errors.append("decision without evidence")
    if not decision.unknowns:
        errors.append("decision without unknowns")
    if not decision.monitoring_items:
        errors.append("decision without monitoring plan")
    if not decision.upgrade_conditions:
        errors.append("decision without upgrade conditions")
    if not decision.downgrade_conditions:
        errors.append("decision without downgrade conditions")
    if not decision.supporting_reasons:
        errors.append("decision without supporting reasons")
    if not decision.contradicting_reasons:
        errors.append("decision without contradicting reasons")
    if decision.decision_graph is None or not decision.decision_graph.nodes:
        errors.append("decision without decision graph")
    if decision.llm:
        errors.append("llm decisions are forbidden")

    return DecisionValidationResult(ok=not errors, errors=errors)
