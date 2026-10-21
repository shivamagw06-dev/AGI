"""Minority report — preserve dissent and its majority trigger."""

from __future__ import annotations

from typing import Any


def build_minority_report(
    positions: list[dict[str, Any]],
    consensus_score: float,
) -> list[dict[str, Any]]:
    minority = []
    majority_positive = consensus_score >= 0.5
    for p in positions:
        score = float(p["position_score"])
        is_minority = (
            majority_positive and score <= 0.3
        ) or (not majority_positive and score >= 0.75)
        if not is_minority:
            continue
        trigger = (
            f"{p['pillar']} falls below its monitored threshold"
            if majority_positive
            else f"{p['pillar']} rises above its constructive threshold"
        )
        minority.append(
            {
                "analyst": p["analyst"],
                "minority_position": p["position"],
                "conclusion": p["conclusion"],
                "confidence": p["confidence"],
                "evidence": (
                    p.get("contradicting_evidence")
                    or p.get("supporting_evidence")
                    or []
                )[:4],
                "conditions_to_become_majority": [trigger]
                + list(p.get("open_questions") or [])[:1],
                "required_evidence": list(p.get("required_evidence") or [])[:4],
                "preserved": True,
            }
        )

    if not minority:
        # Preserve the lowest-scoring analyst even when disagreement is mild.
        p = min(positions, key=lambda row: float(row["position_score"]))
        minority.append(
            {
                "analyst": p["analyst"],
                "minority_position": p["position"],
                "conclusion": p["conclusion"],
                "confidence": p["confidence"],
                "evidence": (
                    p.get("contradicting_evidence")
                    or p.get("supporting_evidence")
                    or []
                )[:4],
                "conditions_to_become_majority": [
                    f"{p['pillar']} breaches its monitored threshold"
                ],
                "required_evidence": list(p.get("required_evidence") or [])[:4],
                "preserved": True,
            }
        )
    return minority
