"""Disagreement engine — explicit pairwise conclusion and confidence conflicts."""

from __future__ import annotations

from typing import Any


def find_disagreements(positions: list[dict[str, Any]]) -> dict[str, Any]:
    conflicts = []
    matrix: dict[str, dict[str, float]] = {
        p["analyst"]: {} for p in positions
    }
    idx = 1
    for i, left in enumerate(positions):
        for right in positions[i + 1 :]:
            gap = abs(float(left["position_score"]) - float(right["position_score"]))
            confidence_gap = abs(float(left["confidence"]) - float(right["confidence"]))
            matrix[left["analyst"]][right["analyst"]] = round(gap, 4)
            matrix[right["analyst"]][left["analyst"]] = round(gap, 4)
            if gap < 0.2 and confidence_gap < 0.18:
                continue
            conflicts.append(
                {
                    "id": f"D-{idx:03d}",
                    "analyst_a": left["analyst"],
                    "position_a": left["position"],
                    "conclusion_a": left["conclusion"],
                    "confidence_a": left["confidence"],
                    "analyst_b": right["analyst"],
                    "position_b": right["position"],
                    "conclusion_b": right["conclusion"],
                    "confidence_b": right["confidence"],
                    "position_gap": round(gap, 4),
                    "confidence_gap": round(confidence_gap, 4),
                    "topic": f"{left['pillar']} vs {right['pillar']}",
                    "type": (
                        "Conflicting Conclusions"
                        if gap >= 0.2
                        else "Different Confidence"
                    ),
                    "unresolved": True,
                }
            )
            idx += 1
    return {
        "conflicts": conflicts,
        "disagreement_count": len(conflicts),
        "matrix": matrix,
        "analysts": [p["analyst"] for p in positions],
        "material_count": sum(
            1 for c in conflicts if c["position_gap"] >= 0.45
        ),
    }
