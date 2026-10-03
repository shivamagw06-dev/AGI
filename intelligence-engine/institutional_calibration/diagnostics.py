"""IDS-02 diagnostics and quality gates."""

from __future__ import annotations

from typing import Any, Optional

from institutional_calibration.models import CalibrationBundle
from institutional_calibration.schema import (
    CALIBRATION_ENGINE_VERSION,
    CAL_VERSION,
    CAL_WORKSTREAM_ID,
    DRIFT_VERSION,
    EXPLAINABILITY_VERSION,
    SCORECARD_VERSION,
)
from institutional_decision.models import InstitutionalDecision


def quality_gates(bundle: CalibrationBundle, decision: InstitutionalDecision) -> dict[str, bool]:
    cal = bundle.calibration
    unexplained = not (cal.positive_contributors or cal.negative_contributors or cal.penalties)
    evidence_ok = cal.evidence_quality is not None and int(cal.evidence_quality) >= 0
    reasons_ok = bool(decision.supporting_reasons) and bool(decision.contradicting_reasons)
    calibration_complete = all(
        [
            cal.final_confidence is not None,
            cal.profile_version,
            cal.evidence_quality is not None,
            cal.reasoning_strength is not None,
            cal.valuation_certainty is not None,
            cal.forecast_stability is not None,
            cal.macro_stability is not None,
        ]
    )
    penalties_defined = cal.unknown_penalty is not None and cal.contradiction_penalty is not None
    bonuses_defined = cal.bonuses is not None  # may be empty list
    confidence_matches = int(decision.confidence) == int(cal.final_confidence)
    calibrated_flag = bool(getattr(decision, "calibrated", False))

    return {
        "confidence_explained": not unexplained,
        "evidence_quality_available": evidence_ok,
        "reason_coverage_complete": reasons_ok,
        "calibration_complete": calibration_complete,
        "penalties_defined": penalties_defined,
        "bonuses_defined": bonuses_defined,
        "confidence_matches_calibration": confidence_matches,
        "decision_calibrated": calibrated_flag,
        "scorecard_present": bool(bundle.scorecard.lines),
        "lineage_complete": bool(bundle.lineage.chain),
        "drift_evaluated": bundle.drift is not None,
    }


def validate_calibration_gates(gates: dict[str, bool]) -> list[str]:
    required = [
        "confidence_explained",
        "evidence_quality_available",
        "reason_coverage_complete",
        "calibration_complete",
        "penalties_defined",
        "bonuses_defined",
        "confidence_matches_calibration",
        "decision_calibrated",
    ]
    errors: list[str] = []
    for key in required:
        if not gates.get(key):
            errors.append(f"quality gate failed: {key}")
    return errors


def build_diagnostics(
    decision: InstitutionalDecision,
    bundle: CalibrationBundle,
    *,
    gate_errors: Optional[list[str]] = None,
) -> dict[str, Any]:
    gates = bundle.quality_gates or quality_gates(bundle, decision)
    return {
        "workstream_id": CAL_WORKSTREAM_ID,
        "calibration_version": CAL_VERSION,
        "calibration_engine_version": CALIBRATION_ENGINE_VERSION,
        "decision_version": decision.decision_version,
        "decision_id": decision.decision_id,
        "evidence_snapshot_id": decision.evidence_snapshot_id,
        "reason_version": decision.reason_version,
        "profile_version": bundle.calibration.profile_version,
        "explainability_version": EXPLAINABILITY_VERSION,
        "drift_version": DRIFT_VERSION,
        "scorecard_version": SCORECARD_VERSION,
        "confidence": decision.confidence,
        "final_confidence": bundle.calibration.final_confidence,
        "confidence_contributors": {
            "positive": [c.to_dict() for c in bundle.calibration.positive_contributors],
            "negative": [c.to_dict() for c in bundle.calibration.negative_contributors],
        },
        "penalty_breakdown": {
            "unknown_penalty": bundle.calibration.unknown_penalty,
            "contradiction_penalty": bundle.calibration.contradiction_penalty,
            "penalties": [c.to_dict() for c in bundle.calibration.penalties],
        },
        "quality_gates": dict(gates),
        "quality_gate_pass": all(gates.get(k) for k in (
            "confidence_explained",
            "evidence_quality_available",
            "reason_coverage_complete",
            "calibration_complete",
            "penalties_defined",
            "bonuses_defined",
            "confidence_matches_calibration",
            "decision_calibrated",
        )),
        "gate_errors": list(gate_errors or []),
        "decision_drift": bundle.drift.to_dict(),
        "lineage": bundle.lineage.to_dict(),
        "llm": False,
    }
