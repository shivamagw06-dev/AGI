"""L4 P0 Shadow constants."""

from __future__ import annotations

MODEL_VERSION = "l4-shadow-vote-0.1.0"
ENGINE_VERSION = "1.0.0"
WEIGHT_SET_ID = "l4_p0_shadow_voters_v1"

# Rule-based directional weights (P0 freeze). E02 is context-only (weight 0).
# E11 is an optional soft voter (≤ social/soft cap 0.05); absent ⇒ weight 0.
VOTER_WEIGHTS: dict[str, float] = {
    "E03": 0.70,
    "E01": 0.20,
    "E14": 0.10,
    "E11": 0.05,
    "E02": 0.00,
}

# Label bands aligned with production research labels for shadow comparison
LABEL_THRESHOLDS = (
    (72.0, "Strong Bullish"),
    (58.0, "Bullish"),
    (43.0, "Neutral"),
    (28.0, "Bearish"),
    (0.0, "Strong Bearish"),
)
