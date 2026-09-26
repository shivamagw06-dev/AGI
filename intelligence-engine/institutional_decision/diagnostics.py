"""Decision diagnostics — always exposed with InstitutionalDecision."""

from __future__ import annotations

from typing import Any

from institutional_decision.models import DecisionValidationResult, InstitutionalDecision
from institutional_decision.schema import DECISION_ENGINE_VERSION, DECISION_VALIDATOR_VERSION, IDS_VERSION


def build_diagnostics(
    decision: InstitutionalDecision,
    validation: DecisionValidationResult | None = None,
) -> dict[str, Any]:
    gate = True
    errors: list[str] = []
    if validation is not None:
        gate = bool(validation.ok)
        errors = list(validation.errors)
    return {
        "recommendation": decision.recommendation,
        "conviction": decision.conviction,
        "confidence": decision.confidence,
        "reason_count": len(decision.supporting_reasons) + len(decision.contradicting_reasons),
        "supporting_reason_count": len(decision.supporting_reasons),
        "contradicting_reason_count": len(decision.contradicting_reasons),
        "evidence_count": len(decision.evidence_ids),
        "supporting_reasons": list(decision.supporting_reasons),
        "contradicting_reasons": list(decision.contradicting_reasons),
        "unknowns": list(decision.unknowns),
        "upgrade_conditions": list(decision.upgrade_conditions),
        "downgrade_conditions": list(decision.downgrade_conditions),
        "monitoring_items": list(decision.monitoring_items),
        "validator_result": "PASS" if gate else "FAIL",
        "validator_errors": errors,
        "decision_id": decision.decision_id,
        "decision_version": decision.decision_version,
        "generated_at": decision.generated_at,
        "reason_version": decision.reason_version,
        "report_version": decision.report_version,
        "evidence_snapshot_id": decision.evidence_snapshot_id,
        "ids_version": IDS_VERSION,
        "decision_engine_version": decision.decision_engine_version or DECISION_ENGINE_VERSION,
        "validator_version": decision.validator_version or DECISION_VALIDATOR_VERSION,
        "score": decision.score,
        "rule_path": decision.rule_path,
        "llm": False,
        "quality_gate_pass": gate,
    }
