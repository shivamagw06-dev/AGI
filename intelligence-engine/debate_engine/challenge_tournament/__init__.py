"""Challenge Tournament — multi-round analyst challenges and position revision."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from debate_engine.schema import POSITION_SCORES, POSITIONS

_ROUNDS = (
    ("Business", "Valuation", "Durable quality may be true, but is it already fully priced?"),
    ("Macro", "Financial", "Could funding costs and the macro path reduce financial resilience?"),
    ("Portfolio", "Business", "Does the thesis survive portfolio concentration constraints?"),
)


def _nearest_position(score: float) -> str:
    return min(POSITIONS, key=lambda p: abs(POSITION_SCORES[p] - score))


def run_tournament(
    positions: list[dict[str, Any]],
    evidence_conflicts: list[dict[str, Any]],
) -> dict[str, Any]:
    revised = deepcopy(positions)
    by_analyst = {p["analyst"]: p for p in revised}
    rounds = []
    for idx, (challenger_name, respondent_name, challenge) in enumerate(_ROUNDS, start=1):
        challenger = by_analyst[challenger_name]
        respondent = by_analyst[respondent_name]
        before_position = respondent["position"]
        before_score = float(respondent["position_score"])
        challenger_score = float(challenger["position_score"])
        evidence = evidence_conflicts[(idx - 1) % max(len(evidence_conflicts), 1)] if evidence_conflicts else {}

        # Revision is evidence-weighted and bounded: respondent moves 20% toward challenger.
        evidence_weight = min(1.0, float(evidence.get("evidence_quality") or 60) / 100.0)
        revised_score = before_score + 0.2 * evidence_weight * (challenger_score - before_score)
        revised_score = round(max(0.0, min(1.0, revised_score)), 4)
        revised_position = _nearest_position(revised_score)
        respondent["position_score"] = revised_score
        respondent["position"] = revised_position
        respondent["confidence"] = round(
            max(0.2, min(0.95, float(respondent["confidence"]) - 0.03 + 0.04 * evidence_weight)),
            4,
        )
        respondent["confidence_pct"] = round(respondent["confidence"] * 100)
        respondent["revision_count"] = int(respondent.get("revision_count") or 0) + 1

        rounds.append(
            {
                "round": idx,
                "challenger": challenger_name,
                "respondent": respondent_name,
                "challenge": challenge,
                "challenger_position": challenger["position"],
                "response": (
                    f"{respondent_name} acknowledges the challenge and recalibrates the position "
                    f"from {before_position} toward {revised_position}."
                ),
                "evidence_considered": {
                    "conflict_id": evidence.get("id"),
                    "quality": evidence.get("evidence_quality"),
                    "required_additional_evidence": evidence.get("required_additional_evidence"),
                },
                "revision": {
                    "from_position": before_position,
                    "to_position": revised_position,
                    "from_score": before_score,
                    "to_score": revised_score,
                    "confidence_after": respondent["confidence"],
                },
                "consensus_recalculation_required": True,
            }
        )
    return {
        "rounds": rounds,
        "round_count": len(rounds),
        "revised_positions": revised,
        "revision_count": sum(int(p.get("revision_count") or 0) for p in revised),
        "completed": True,
    }
