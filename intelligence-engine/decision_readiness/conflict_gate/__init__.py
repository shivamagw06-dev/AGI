"""Debate/conflict gate — consensus, minority preservation and unresolved issues."""

from __future__ import annotations

from typing import Any


def evaluate_debate(debate: dict[str, Any]) -> dict[str, Any]:
    consensus = debate.get("consensus") or {}
    disagreement = debate.get("disagreement") or {}
    minority = debate.get("minority_report") or []
    audit = debate.get("audit") or {}
    conflicts = disagreement.get("conflicts") or []
    material = int(disagreement.get("material_count") or 0)
    unresolved = [c for c in conflicts if c.get("unresolved", True)]
    open_questions = list(debate.get("open_questions") or [])
    agreement = float(consensus.get("agreement") or 0)
    confidence = float(consensus.get("confidence") or 0)
    evidence_sufficiency = float(consensus.get("evidence_sufficiency") or 0)
    minority_preserved = bool(minority) and all(
        m.get("preserved") for m in minority
    )
    conflicts_resolved = material == 0 or bool(consensus.get("vote_ready"))
    score = (
        0.30 * agreement
        + 0.20 * confidence
        + 0.20 * evidence_sufficiency
        + 0.15 * (1.0 if minority_preserved else 0.0)
        + 0.15 * max(0.0, 1.0 - material / 6.0)
    )
    if not (audit.get("passed", True)):
        score -= 0.12
    score = max(0.0, min(1.0, score))
    return {
        "dimension": "Debate",
        "score": round(score, 4),
        "score_pct": round(score * 100),
        "passed": conflicts_resolved and minority_preserved and agreement >= 0.6,
        "checks": {
            "major_conflicts_resolved": conflicts_resolved,
            "minority_report_preserved": minority_preserved,
            "consensus_strength": round(agreement, 4),
            "evidence_sufficiency": round(evidence_sufficiency, 4),
            "debate_audit_complete": bool(audit.get("passed", True)),
        },
        "remaining_conflicts": unresolved[:12],
        "outstanding_questions": open_questions[:12],
        "minority_reviewed": minority_preserved,
        "strengths": [
            "Minority report preserved" if minority_preserved else None,
            "Constructive consensus" if agreement >= 0.6 else None,
            "Evidence conflicts mapped" if debate.get("evidence_conflicts") else None,
        ],
        "weaknesses": [
            f"{material} material conflicts remain" if material else None,
            f"{len(open_questions)} questions remain open" if open_questions else None,
            "Consensus below institutional threshold" if agreement < 0.6 else None,
        ],
    }
