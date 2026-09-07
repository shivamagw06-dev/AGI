"""E11-005 Soft voter adapter — absent E11 ⇒ L4 weight 0 (chaos acceptance)."""

from __future__ import annotations

from typing import Any

from app.engines.e11.mapping import SOCIAL_WEIGHT_CAP, SOFT_VOTER_WEIGHT
from app.engines.e11.sentiment_state import E11State


def soft_voter_contribution(sent: E11State | None) -> dict[str, Any]:
    """Return L4 soft-voter payload. Missing state → weight 0, no influence."""
    if sent is None:
        return {
            "engine": "E11",
            "present": False,
            "weight": 0.0,
            "signed": 0.0,
            "confidence": 0.0,
            "social_weight_cap": SOCIAL_WEIGHT_CAP,
            "social_enabled": False,
            "note": "absent_voter_weight_zero",
        }
    signed = max(-1.0, min(1.0, (sent.composite_score - 50.0) / 50.0))
    w = min(float(sent.soft_voter_weight or 0.0), SOFT_VOTER_WEIGHT, SOCIAL_WEIGHT_CAP)
    if sent.social_enabled:
        w = min(w, SOCIAL_WEIGHT_CAP)
    else:
        # social disabled — soft news weight still capped by production social rule envelope
        w = min(w, SOCIAL_WEIGHT_CAP)
    return {
        "engine": "E11",
        "present": True,
        "weight": round(w, 6),
        "signed": round(signed, 6),
        "confidence": round(float(sent.confidence), 6),
        "score": sent.composite_score,
        "social_weight_cap": SOCIAL_WEIGHT_CAP,
        "social_enabled": False,
        "note": "soft_voter",
    }
