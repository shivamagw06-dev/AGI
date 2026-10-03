"""Decision drift — previous → current recommendation / confidence / reason / evidence."""

from __future__ import annotations

from typing import Optional, Sequence

from institutional_calibration.models import DecisionDrift
from institutional_calibration.schema import DRIFT_VERSION
from institutional_decision.models import InstitutionalDecision


def detect_drift(
    current: InstitutionalDecision,
    previous: Optional[InstitutionalDecision],
    *,
    current_reasons: Sequence[str] | None = None,
    previous_reasons: Sequence[str] | None = None,
) -> DecisionDrift:
    if previous is None:
        return DecisionDrift(
            has_previous=False,
            previous_recommendation=None,
            current_recommendation=current.recommendation,
            recommendation_changed=False,
            previous_confidence=None,
            current_confidence=int(current.confidence),
            confidence_delta=None,
            reason_changes=[],
            evidence_changes=[],
            explanation_chain=["No previous decision — drift baseline established"],
            previous_decision_id=None,
            current_decision_id=current.decision_id,
        )

    prev_rec = str(previous.recommendation or "").upper()
    cur_rec = str(current.recommendation or "").upper()
    rec_changed = prev_rec != cur_rec
    prev_conf = int(previous.confidence)
    cur_conf = int(current.confidence)
    delta = cur_conf - prev_conf

    prev_reasons = set(previous_reasons or previous.supporting_reasons or ())
    cur_reasons = set(current_reasons or current.supporting_reasons or ())
    added = sorted(cur_reasons - prev_reasons)
    removed = sorted(prev_reasons - cur_reasons)
    reason_changes: list[str] = []
    for r in added[:6]:
        reason_changes.append(f"+ {r}")
    for r in removed[:6]:
        reason_changes.append(f"- {r}")

    prev_ev = set(previous.evidence_ids or ())
    cur_ev = set(current.evidence_ids or ())
    evidence_changes: list[str] = []
    for e in sorted(cur_ev - prev_ev)[:6]:
        evidence_changes.append(f"+ {e}")
    for e in sorted(prev_ev - cur_ev)[:6]:
        evidence_changes.append(f"- {e}")

    chain: list[str] = [f"Previous: {prev_rec}", f"Current: {cur_rec}"]
    if rec_changed:
        chain.append(f"Recommendation changed {prev_rec} → {cur_rec}")
    else:
        chain.append("Recommendation unchanged")

    # Infer dominant drivers from rule_path / score deltas
    if previous.score != current.score:
        chain.append(f"Decision score {previous.score} → {current.score}")
    if "val:" in (current.rule_path or "") and "Expensive" in (current.rule_path or ""):
        chain.append("Valuation premium increased / remains expensive")
    if delta < 0:
        chain.append("Confidence decreased")
    elif delta > 0:
        chain.append("Confidence increased")
    else:
        chain.append("Confidence unchanged")

    if reason_changes:
        chain.append("Reason set changed")
    if evidence_changes:
        chain.append("Evidence set changed")

    # Parse rule path diffs for readable drift
    prev_parts = set((previous.rule_path or "").split("|"))
    cur_parts = set((current.rule_path or "").split("|"))
    for part in sorted(cur_parts - prev_parts):
        if part:
            chain.append(f"Rule factor now: {part}")
    for part in sorted(prev_parts - cur_parts):
        if part:
            chain.append(f"Rule factor removed: {part}")

    return DecisionDrift(
        has_previous=True,
        previous_recommendation=prev_rec,
        current_recommendation=cur_rec,
        recommendation_changed=rec_changed,
        previous_confidence=prev_conf,
        current_confidence=cur_conf,
        confidence_delta=delta,
        reason_changes=reason_changes,
        evidence_changes=evidence_changes,
        explanation_chain=chain[:16],
        previous_decision_id=previous.decision_id,
        current_decision_id=current.decision_id,
    )


def drift_meta() -> dict:
    return {"drift_version": DRIFT_VERSION}
