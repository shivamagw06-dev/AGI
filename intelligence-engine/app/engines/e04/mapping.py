"""E04 P0 statistical arbitrage / relative value bindings."""

from __future__ import annotations

MODEL_VERSION = "e04-p0-stat-arb-0.1.0"
ENGINE_VERSION = "1.0.0"
FORMULA_ID = "RV_AGI_PAIR"

# Default lookback for OLS / EG / half-life when series provided
DEFAULT_LOOKBACK = 60

REGISTRY_RVAL: tuple[str, ...] = (
    "RVAL_SPREAD",
    "RVAL_COINTEGRATION",
    "RVAL_HALF_LIFE",
)

# Z-score thresholds for labels
Z_RICH = 1.5
Z_CHEAP = -1.5
