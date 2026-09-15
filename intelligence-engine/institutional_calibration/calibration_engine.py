"""IDS-02 Calibration Engine — public API: calibrate_decision(...)."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Optional, Sequence, Union

from institutional_calibration.confidence import compute_calibration, confidence_breakdown_dict
from institutional_calibration.diagnostics import build_diagnostics, quality_gates, validate_calibration_gates
from institutional_calibration.drift import detect_drift
from institutional_calibration.explainability import build_explainability
from institutional_calibration.models import (
    CalibrationBundle,
    DecisionLineage,
    DecisionScorecard,
    ScorecardLine,
)
from institutional_calibration.profile import CalibrationProfile, DEFAULT_PROFILE
from institutional_calibration.schema import (
    CALIBRATION_ENGINE_VERSION,
    CAL_VERSION,
)
from institutional_calibration.scoring import collect_component_scores, scorecard_lines
from institutional_decision.models import InstitutionalDecision
from institutional_reporting.models import InstitutionalReportInput
from institutional_reporting.reasoning import Reason


def _as_reasons(reasons: Any) -> list[Reason]:
    if reasons is None:
        return []
    if hasattr(reasons, "reasons"):
        return list(reasons.reasons or [])
    out: list[Reason] = []
    for item in reasons:
        if isinstance(item, Reason):
            out.append(item)
        elif isinstance(item, dict):
            out.append(Reason.from_dict(item))
    return out


def _build_lineage(
    decision: InstitutionalDecision,
    reasons: Sequence[Reason],
    *,
    profile_version: str,
) -> DecisionLineage:
    reason_ids = []
    for r in reasons:
        key = r.section_key or r.title or "reason"
        reason_ids.append(str(key))
    chain = [
        "Evidence",
        "Reason Objects",
        "Decision",
        "Calibration",
        "Report",
    ]
    return DecisionLineage(
        evidence_snapshot_id=decision.evidence_snapshot_id,
        reason_ids=reason_ids,
        reason_version=decision.reason_version,
        decision_id=decision.decision_id,
        decision_version=str(decision.decision_version),
        calibration_version=CAL_VERSION,
        profile_version=profile_version,
        report_version=decision.report_version,
        chain=chain,
    )


def calibrate_decision(
    decision: InstitutionalDecision,
    reasons: Any = None,
    evidence: Union[InstitutionalReportInput, dict, None] = None,
    *,
    previous: Optional[InstitutionalDecision] = None,
    profile: Optional[CalibrationProfile] = None,
) -> tuple[InstitutionalDecision, CalibrationBundle]:
    """
    Public API.

    calibrate_decision(decision, reasons, evidence) → Calibration → updated InstitutionalDecision

    Confidence is computed, never manually assigned.
    """
    profile = profile or DEFAULT_PROFILE
    reason_list = _as_reasons(reasons)
    if isinstance(evidence, InstitutionalReportInput):
        payload = evidence
    else:
        payload = InstitutionalReportInput.from_dict(evidence or {})

    components = collect_component_scores(decision, reason_list, payload)
    calibration = compute_calibration(components, profile=profile)

    lines_raw, total = scorecard_lines(
        decision, payload, unknown_penalty=calibration.unknown_penalty
    )
    scorecard = DecisionScorecard(
        lines=[ScorecardLine(**row) for row in lines_raw],
        recommendation=decision.recommendation,
        confidence=calibration.final_confidence,
        total_points=total,
    )
    explainability = build_explainability(
        decision, reason_list, payload, calibration, scorecard
    )

    # Apply calibrated confidence onto an updated decision (immutable replace)
    updated = replace(
        decision,
        confidence=int(calibration.final_confidence),
        calibrated=True,
        calibration_version=CAL_VERSION,
        calibration_profile_version=profile.profile_version,
        calibration_engine_version=CALIBRATION_ENGINE_VERSION,
        calibration=calibration,
    )

    drift = detect_drift(updated, previous)
    lineage = _build_lineage(updated, reason_list, profile_version=profile.profile_version)

    bundle = CalibrationBundle(
        calibration=calibration,
        scorecard=scorecard,
        explainability=explainability,
        drift=drift,
        lineage=lineage,
        diagnostics={},
        quality_gates={},
    )
    gates = quality_gates(bundle, updated)
    gate_errors = validate_calibration_gates(gates)
    diagnostics = build_diagnostics(updated, replace_bundle_gates(bundle, gates), gate_errors=gate_errors)
    bundle = CalibrationBundle(
        calibration=calibration,
        scorecard=scorecard,
        explainability=explainability,
        drift=drift,
        lineage=lineage,
        diagnostics=diagnostics,
        quality_gates=gates,
    )
    return updated, bundle


def replace_bundle_gates(bundle: CalibrationBundle, gates: dict) -> CalibrationBundle:
    return CalibrationBundle(
        calibration=bundle.calibration,
        scorecard=bundle.scorecard,
        explainability=bundle.explainability,
        drift=bundle.drift,
        lineage=bundle.lineage,
        diagnostics=bundle.diagnostics,
        quality_gates=gates,
    )


def calibration_summary(bundle: CalibrationBundle) -> dict[str, Any]:
    return {
        "recommendation_confidence": bundle.calibration.final_confidence,
        "breakdown": confidence_breakdown_dict(bundle.calibration),
        "scorecard": bundle.scorecard.to_dict(),
        "explainability": bundle.explainability.to_dict(),
        "drift": bundle.drift.to_dict(),
        "lineage": bundle.lineage.to_dict(),
        "quality_gates": dict(bundle.quality_gates),
        "diagnostics": dict(bundle.diagnostics),
    }
