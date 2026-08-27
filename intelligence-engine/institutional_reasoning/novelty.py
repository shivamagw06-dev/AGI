"""Novelty score — prevent overfitting to memorised gold cases.

Before answering, ask: have I seen this exact pattern before?
Yes → use the reasoning family / gold habit.
No  → reason from first principles; do not force the closest template.
"""

from __future__ import annotations

from typing import Any


def score_novelty(
    *,
    gold_exact: bool,
    family_id: str | None,
    family_confidence: float,
    first_principles: bool,
    adversarial: bool = False,
    novelty_band_hint: str | None = None,
) -> dict[str, Any]:
    """Return novelty diagnostics.

    Scale 0–1:
      ~0.0–0.25  seen exact gold pattern
      ~0.35–0.65  same family, new facts (generalisation)
      ~0.70–0.90  first-principles family compose
      ~0.90–1.00  hard / dual-hypothesis / adversarial unseen structure
    """
    if gold_exact:
        return {
            "novelty_score": 0.15,
            "band": "seen_exact",
            "guidance": "use_reasoning_family",
            "force_closest_template": False,
            "family_id": family_id,
            "note": "Exact gold pattern recognised — apply the trained habit, not rote copy of unrelated cases.",
        }

    if adversarial:
        band = novelty_band_hint or "hard_unseen"
        score = 0.97 if band == "hard_unseen" else 0.78 if band == "first_principles" else 0.55
        return {
            "novelty_score": score,
            "band": band if band in {"hard_unseen", "first_principles", "same_family_new_facts"} else "hard_unseen",
            "guidance": "reason_from_first_principles",
            "force_closest_template": False,
            "family_id": family_id,
            "adversarial": True,
            "note": (
                "Adversarial / unknown structure — decompose, respect evidence boundaries, "
                "and do not force the closest memorised template."
            ),
        }

    if family_id == "dual_hypothesis":
        return {
            "novelty_score": 0.95,
            "band": "hard_unseen",
            "guidance": "first_principles_dual_hypothesis",
            "force_closest_template": False,
            "family_id": family_id,
            "note": "No memorised answer. Hold two explanations open; do not decide.",
        }

    if family_id and family_confidence >= 0.55:
        # Same family, different facts — the Phase-2 generalisation band.
        score = 0.45 + (0.25 * (1.0 - min(family_confidence, 1.0)))
        if first_principles:
            score = max(score, 0.72)
        return {
            "novelty_score": round(min(score, 0.88), 3),
            "band": "same_family_new_facts" if not first_principles else "first_principles",
            "guidance": "use_reasoning_family" if not first_principles else "reason_from_first_principles",
            "force_closest_template": False,
            "family_id": family_id,
            "note": (
                "Familiar reasoning family with novel facts — generalise the habit; "
                "do not force the closest memorised template."
            ),
        }

    return {
        "novelty_score": 1.0,
        "band": "unclassified",
        "guidance": "do_not_force_template",
        "force_closest_template": False,
        "family_id": family_id,
        "note": "No family confidently matched — withhold templated certainty.",
    }


__all__ = ["score_novelty"]
