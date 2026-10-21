"""Consensus engine — consensus, confidence, sufficiency and debate state."""

from __future__ import annotations

from statistics import pstdev
from typing import Any

from debate_engine.schema import DEBATE_STATES


def build_consensus(
    positions: list[dict[str, Any]],
    disagreements: dict[str, Any],
    evidence_conflicts: list[dict[str, Any]],
    open_questions: list[str],
) -> dict[str, Any]:
    scores = [float(p["position_score"]) for p in positions]
    confidences = [float(p["confidence"]) for p in positions]
    mean_score = sum(scores) / max(len(scores), 1)
    dispersion = pstdev(scores) if len(scores) > 1 else 0.0
    agreement_pct = round(max(0.0, min(1.0, 1.0 - dispersion / 0.5)), 4)
    evidence_sufficiency = round(
        sum(float(c.get("evidence_quality") or 0) for c in evidence_conflicts)
        / max(len(evidence_conflicts), 1)
        / 100.0,
        4,
    )
    consensus_confidence = round(
        max(
            0.1,
            min(
                0.95,
                0.45 * agreement_pct
                + 0.3 * (sum(confidences) / max(len(confidences), 1))
                + 0.25 * evidence_sufficiency,
            ),
        ),
        4,
    )

    material = int(disagreements.get("material_count") or 0)
    conflict_count = int(disagreements.get("disagreement_count") or 0)
    if evidence_sufficiency < 0.45:
        state = "Evidence Insufficient"
    elif agreement_pct >= 0.82 and material == 0:
        state = "Consensus"
    elif agreement_pct >= 0.62 and material <= 2:
        state = "Constructive Disagreement"
    elif agreement_pct >= 0.38:
        state = "Material Disagreement"
    else:
        state = "Deadlock"
    assert state in DEBATE_STATES
    return {
        "state": state,
        "consensus_score": round(mean_score, 4),
        "consensus_score_pct": round(mean_score * 100),
        "agreement": agreement_pct,
        "agreement_pct": round(agreement_pct * 100),
        "dispersion": round(dispersion, 4),
        "confidence": consensus_confidence,
        "confidence_pct": round(consensus_confidence * 100),
        "evidence_sufficiency": evidence_sufficiency,
        "evidence_sufficiency_pct": round(evidence_sufficiency * 100),
        "outstanding_issues": open_questions[:10],
        "conflict_count": conflict_count,
        "material_conflict_count": material,
        "vote_ready": state in ("Consensus", "Constructive Disagreement"),
    }
