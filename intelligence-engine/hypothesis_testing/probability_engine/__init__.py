"""Probability engine — update belief from qualitative evidence effects."""

from __future__ import annotations

from typing import Any

from hypothesis_testing.schema import EFFECT_DELTAS


def _clamp(p: float) -> float:
    return round(max(0.05, min(0.95, p)), 4)


def update_probability(
    initial_confidence: float,
    evidence: list[dict[str, Any]],
    *,
    missing_penalty: float = 0.0,
) -> dict[str, Any]:
    p = float(initial_confidence)
    timeline = [{"step": "initial", "probability": _clamp(p), "delta": 0.0, "note": "Initial confidence"}]
    net = 0.0
    for e in evidence:
        if e.get("effect") == "Neutral" and str(e.get("polarity") or "") == "missing":
            continue
        delta = float(e.get("probability_delta") if e.get("probability_delta") is not None else EFFECT_DELTAS.get(str(e.get("effect") or "Neutral"), 0.0))
        # Scale mild dampening when many items (avoid explosion)
        scaled = delta * 0.85
        p = _clamp(p + scaled)
        net += scaled
        timeline.append(
            {
                "step": "evidence",
                "evidence_id": e.get("id"),
                "effect": e.get("effect"),
                "delta": round(scaled, 4),
                "probability": p,
                "note": f"{e.get('effect')}: {e.get('text')}",
            }
        )
    if missing_penalty:
        p = _clamp(p - abs(missing_penalty))
        net -= abs(missing_penalty)
        timeline.append(
            {
                "step": "missing_data",
                "delta": round(-abs(missing_penalty), 4),
                "probability": p,
                "note": "Missing evidence penalty",
            }
        )
    return {
        "initial_confidence": round(float(initial_confidence), 4),
        "updated_probability": p,
        "net_delta": round(net, 4),
        "timeline": timeline,
    }


def status_from_probability(
    probability: float,
    *,
    support_count: int,
    contradiction_count: int,
    has_refutation: bool,
) -> str:
    if has_refutation or (probability < 0.35 and contradiction_count >= 2):
        return "Rejected" if probability < 0.28 or has_refutation else "Contradicted"
    if probability >= 0.72 and support_count >= 5 and contradiction_count <= 2:
        return "Supported"
    if probability >= 0.55:
        return "Partially Supported"
    if support_count < 3 and contradiction_count < 2:
        return "Inconclusive"
    if contradiction_count > support_count:
        return "Contradicted"
    return "Inconclusive"
