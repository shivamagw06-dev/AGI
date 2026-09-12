"""Deterministic CRE validation and point-in-time gates."""

from __future__ import annotations

from typing import Any

from causal_research_engine.schema import (
    CONTRADICTION_STATUSES, DIRECTIONS, EPISTEMIC_LABELS, KNOWLEDGE_STATUSES,
    RELATIONSHIP_TYPES, SCENARIOS, STRENGTHS, TIME_LAGS, CausalRelationship,
    ContradictionGroup, FinancialImpact,
)


def _date(value: str | None) -> str:
    return str(value or "")[:10]


def validate_relationship(row: CausalRelationship, *, analysis_as_of: str | None = None) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if not row.relationship_id or not row.cause or not row.effect:
        errors.append("IDENTITY_INCOMPLETE")
    if row.direction not in DIRECTIONS: errors.append("INVALID_DIRECTION")
    if row.relationship_type not in RELATIONSHIP_TYPES: errors.append("INVALID_RELATIONSHIP_TYPE")
    if row.epistemic_label not in EPISTEMIC_LABELS: errors.append("INVALID_EPISTEMIC_LABEL")
    if row.strength not in STRENGTHS: errors.append("INVALID_STRENGTH")
    if row.time_lag not in TIME_LAGS: errors.append("INVALID_TIME_LAG")
    if row.status not in KNOWLEDGE_STATUSES: errors.append("INVALID_KNOWLEDGE_STATUS")
    if not 0.0 <= float(row.confidence) <= 1.0: errors.append("INVALID_CONFIDENCE")
    if row.fabricated: errors.append("FABRICATED_CONTENT")
    if row.relationship_type != "CAUSAL_HYPOTHESIS" and not row.mechanism:
        errors.append("MECHANISM_REQUIRED")
    evidence_ids = [item.evidence_id for item in row.evidence if item.evidence_id]
    if len(evidence_ids) != len(set(evidence_ids)): warnings.append("DUPLICATE_EVIDENCE_ID")
    if row.source_count and row.source_count != len({item.primary_source_id or item.source_id for item in row.evidence}):
        errors.append("SOURCE_COUNT_MISMATCH")
    if not row.evidence:
        if row.relationship_type != "CAUSAL_HYPOTHESIS" or row.status != "PROPOSED":
            errors.append("EVIDENCE_REQUIRED")
        else:
            warnings.append("HYPOTHESIS_WITHOUT_EVIDENCE")
    if row.status in {"VALIDATED", "TRUSTED"} and any(item.quality == "UNVALIDATED" for item in row.evidence):
        errors.append("UNVALIDATED_EVIDENCE")
    if row.status == "TRUSTED" and row.source_quality == "UNVALIDATED":
        errors.append("TRUST_REQUIRES_SOURCE_QUALITY")
    if analysis_as_of:
        future = [item.evidence_id for item in row.evidence if _date(item.available_at) and _date(item.available_at) > _date(analysis_as_of)]
        if future: errors.append("POINT_IN_TIME_VIOLATION")
    if row.valid_from and row.valid_to and _date(row.valid_from) > _date(row.valid_to):
        errors.append("INVALID_VALIDITY_WINDOW")
    return {"ok": not errors, "relationship_id": row.relationship_id, "errors": errors, "warnings": warnings}


def validate_contradiction(row: ContradictionGroup) -> dict[str, Any]:
    errors = []
    if len(set(row.relationship_ids)) < 2: errors.append("CONTRADICTION_REQUIRES_TWO_RELATIONSHIPS")
    if row.status not in CONTRADICTION_STATUSES: errors.append("INVALID_CONTRADICTION_STATUS")
    if row.status == "RESOLVED" and not row.resolution: errors.append("RESOLUTION_REQUIRED")
    return {"ok": not errors, "contradiction_id": row.contradiction_id, "errors": errors}


def validate_financial_impact(row: FinancialImpact) -> dict[str, Any]:
    errors = []
    if row.direction not in DIRECTIONS: errors.append("INVALID_DIRECTION")
    if row.epistemic_label not in {"CALCULATION", "SCENARIO", "FORECAST", "HYPOTHESIS"}:
        errors.append("INVALID_FINANCIAL_IMPACT_LABEL")
    if row.epistemic_label == "CALCULATION" and (not row.calculation_id or not row.afe_result):
        errors.append("AFE_RESULT_REQUIRED")
    if row.epistemic_label in {"SCENARIO", "FORECAST"} and row.scenario not in SCENARIOS:
        errors.append("SCENARIO_REQUIRED")
    if row.epistemic_label in {"SCENARIO", "FORECAST", "HYPOTHESIS"} and not row.assumptions:
        errors.append("ASSUMPTIONS_REQUIRED")
    if row.status not in KNOWLEDGE_STATUSES: errors.append("INVALID_KNOWLEDGE_STATUS")
    if not 0.0 <= float(row.confidence) <= 1.0: errors.append("INVALID_CONFIDENCE")
    return {"ok": not errors, "impact_id": row.impact_id, "errors": errors}
