"""Recommendation / fact / reason consistency validators — run before rendering."""

from __future__ import annotations

from institutional_reporting.models import InstitutionalReportInput, ValidationResult
from institutional_reporting.recommendation import (
    business_quality_band,
    is_known_conviction,
    is_known_recommendation,
    normalize_conviction,
    normalize_recommendation,
    recommendation_requires_conviction,
)
from institutional_reporting.reasoning import Reason, ReasonGraph
from institutional_reporting.schema import HORIZONS, REPORT_SECTIONS, RISK_LABELS, VALUATION_LABELS


def validate_input(inp: InstitutionalReportInput) -> ValidationResult:
    errors: list[str] = []

    if not inp.ticker:
        errors.append("ticker is required")
    if not inp.company_name:
        errors.append("company_name is required")
    if not inp.sector:
        errors.append("sector is required")

    rec = normalize_recommendation(inp.recommendation)
    conv = normalize_conviction(inp.conviction)

    if not is_known_recommendation(rec):
        errors.append(f"recommendation must be one of {sorted(RECOMMENDATIONS_SAFE)}")
    if not is_known_conviction(conv):
        errors.append(f"conviction must be one of {sorted(CONVICTIONS_SAFE)}")

    if is_known_recommendation(rec) and is_known_conviction(conv):
        allowed = recommendation_requires_conviction(rec)
        if conv not in allowed:
            errors.append(
                f"impossible combination: recommendation={rec} with conviction={conv} "
                f"(requires {sorted(allowed)})"
            )

    if not isinstance(inp.confidence, int) or inp.confidence < 0 or inp.confidence > 100:
        errors.append("confidence must be an integer between 0 and 100")

    horizon = str(inp.horizon or "").strip()
    if horizon not in HORIZONS:
        errors.append(f"horizon must be one of {list(HORIZONS)}")

    valuation = str(inp.valuation or "").strip().title()
    if valuation not in VALUATION_LABELS:
        errors.append(f"valuation must be one of {list(VALUATION_LABELS)}")

    risk = str(inp.overall_risk or "").strip().title()
    if risk not in RISK_LABELS:
        errors.append(f"overall_risk must be one of {list(RISK_LABELS)}")

    if not str(inp.financial_quality or "").strip():
        errors.append("financial_quality is required")

    bq = inp.business_quality
    if bq == "" or bq is None:
        errors.append("business_quality is required")
    elif isinstance(bq, (int, float)) and (float(bq) < 0 or float(bq) > 100):
        errors.append("business_quality numeric score must be between 0 and 100")

    # Institutional contradiction: SELL while excellent franchise is cheap and low risk
    if rec == "SELL":
        band = business_quality_band(inp.business_quality)
        if band == "Excellent" and valuation == "Cheap" and risk == "Low":
            errors.append(
                "impossible combination: SELL with Excellent business quality, Cheap valuation, Low risk"
            )

    # BUY while expensive + high/severe risk + weak quality is contradictory without HIGH conviction nuance;
    # hard-fail only the clearest contradiction.
    if rec == "BUY" and business_quality_band(inp.business_quality) == "Weak" and valuation == "Expensive":
        errors.append(
            "impossible combination: BUY with Weak business quality and Expensive valuation"
        )

    if not inp.thesis:
        errors.append("thesis must contain at least one fact bullet")
    if not inp.evidence:
        errors.append("evidence must contain at least one evidence item")
    else:
        for i, ev in enumerate(inp.evidence):
            if not ev.evidence_id:
                errors.append(f"evidence[{i}].evidence_id is required")
            if not ev.label:
                errors.append(f"evidence[{i}].label is required")

    return ValidationResult(ok=not errors, errors=errors)


def validate_reason(reason: Reason, *, section_key: str = "") -> list[str]:
    """Reason Validator — every conclusion must be supported, contradicted, evidenced, unknown-aware."""
    errors: list[str] = []
    label = section_key or reason.section_key or reason.title or "reason"
    if not str(reason.title or "").strip():
        errors.append(f"{label}: reason missing title")
    if not str(reason.conclusion or "").strip():
        errors.append(f"{label}: reason missing conclusion")
    try:
        conf = float(reason.confidence)
    except (TypeError, ValueError):
        conf = -1.0
        errors.append(f"{label}: reason missing confidence")
    else:
        if conf < 0.0 or conf > 1.0:
            errors.append(f"{label}: reason confidence must be between 0 and 1")
    if not reason.supporting_points:
        errors.append(f"{label}: reason missing supporting points")
    if not reason.contradicting_points:
        errors.append(f"{label}: reason missing contradicting evidence")
    if not reason.unknowns:
        errors.append(f"{label}: reason missing unknowns")
    if not reason.supporting_evidence:
        errors.append(f"{label}: reason missing evidence")
    # Empty reason object
    if (
        not reason.conclusion
        and not reason.supporting_points
        and not reason.contradicting_points
        and not reason.unknowns
        and not reason.supporting_evidence
    ):
        errors.append(f"{label}: empty reason object")
    return errors


def validate_reasons(graph: ReasonGraph) -> ValidationResult:
    errors: list[str] = []
    by_key = graph.by_section()
    for key in REPORT_SECTIONS:
        reason = by_key.get(key)
        if reason is None:
            errors.append(f"section missing reason: {key}")
            continue
        errors.extend(validate_reason(reason, section_key=key))
    if len(graph.reasons) != len(REPORT_SECTIONS):
        errors.append(
            f"reason count mismatch: expected {len(REPORT_SECTIONS)}, got {len(graph.reasons)}"
        )
    return ValidationResult(ok=not errors, errors=errors)


# Local aliases so error messages stay stable if schema tuples change import style.
RECOMMENDATIONS_SAFE = ("BUY", "HOLD", "SELL", "AVOID", "WATCH")
CONVICTIONS_SAFE = ("LOW", "MEDIUM", "HIGH")
