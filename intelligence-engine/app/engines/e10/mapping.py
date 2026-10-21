"""E10 P0 constants — frozen policy defaults."""

from __future__ import annotations

MODEL_VERSION = "e10-p0-invvol-0.1.0"
ENGINE_VERSION = "1.0.0"
SOLVER_ID = "AM_INVVOL"
MANDATE_ID = "AGI_CORE_LO_P0"
BOOK_ID = "research_core_p0"
PORTFOLIO_TYPE = "P_LONG_ONLY"

# Selection
TOP_N_DEFAULT = 10
MIN_L4_SCORE = 58.0  # Bullish threshold band
ELIGIBLE_LABELS = frozenset({"Bullish", "Strong Bullish"})

# Risk caps (research defaults / E14 name cap policy)
NAME_CAP = 0.08
SECTOR_CAP = 0.25
DEFAULT_SIGMA = 0.25
MIN_SIGMA = 0.08
MAX_SIGMA = 0.60

# Vol targeting
DEFAULT_VOL_TARGET = 0.12

# Cash floors by E14 playbook / risk_level
CASH_FLOOR = {
    "normal": 0.05,
    "elevated": 0.15,
    "hard_derisk": 0.35,
    "research_hedge_only": 0.40,
}
CASH_FLOOR_BY_RISK = {
    "low": 0.05,
    "moderate": 0.05,
    "elevated": 0.15,
    "severe": 0.30,
    "critical": 0.40,
}
