"""Qualitative evidence effects — Confirms / Supports / … / Refutes."""

from __future__ import annotations

from typing import Any

from hypothesis_testing.schema import EFFECT_DELTAS, EVIDENCE_EFFECTS


def classify_effect(item: dict[str, Any]) -> str:
    """Map polarity + strength into a qualitative effect label."""
    polarity = str(item.get("polarity") or "neutral").lower()
    strength = int(item.get("strength") or 0)
    kind = str(item.get("kind") or "").lower()

    if polarity in ("missing",) or kind == "missing" or "incomplete" in str(item.get("text") or "").lower():
        return "Neutral"

    if polarity in ("support", "supports", "confirm", "positive"):
        if strength >= 88:
            return "Confirms"
        if strength >= 70:
            return "Supports"
        if strength >= 50:
            return "Weakly Supports"
        return "Neutral"

    if polarity in ("contradict", "contradicts", "negative", "refute"):
        if strength >= 85:
            return "Refutes"
        if strength >= 60:
            return "Contradicts"
        if strength >= 40:
            return "Questions"
        return "Neutral"

    # Neutral / unknown polarity — keyword nudge
    text = str(item.get("text") or "").lower()
    if any(x in text for x in ("above peer", "superior", "remained above", "structurally better")):
        return "Supports" if strength >= 70 else "Weakly Supports"
    if any(x in text for x in ("slowed", "compressed", "acknowledged", "pressure", "ticked up")):
        return "Questions" if strength < 70 else "Contradicts"
    return "Neutral"


def attach_effects(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for item in evidence:
        effect = classify_effect(item)
        if effect not in EVIDENCE_EFFECTS:
            effect = "Neutral"
        out.append(
            {
                **item,
                "effect": effect,
                "probability_delta": float(EFFECT_DELTAS.get(effect, 0.0)),
                "support_score": int(item.get("strength") or 0) if effect in ("Confirms", "Supports", "Weakly Supports") else 0,
                "contradiction_score": int(item.get("strength") or 0)
                if effect in ("Questions", "Contradicts", "Refutes")
                else 0,
            }
        )
    return out


def effect_breakdown(evidence: list[dict[str, Any]]) -> dict[str, int]:
    counts = {e: 0 for e in EVIDENCE_EFFECTS}
    for item in evidence:
        e = str(item.get("effect") or "Neutral")
        counts[e] = counts.get(e, 0) + 1
    return counts
