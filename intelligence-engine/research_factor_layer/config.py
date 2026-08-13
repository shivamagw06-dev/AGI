"""Versioned factor methodologies. Weights live here, never in UI code."""

QUALITY_VERSION = "quality-compounder-v1.0.0"
MISPRICING_VERSION = "relative-mispricing-v1.0.0"

QUALITY_WEIGHTS = {
    "roic_5y": 0.30,
    "fcf_margin": 0.20,
    "fcf_conversion": 0.15,
    "roic_stability": 0.15,
    "reinvestment": 0.10,
    "balance_sheet": 0.10,
}

MISPRICING_WEIGHTS = {
    "pe": 0.30,
    "ev_ebitda": 0.30,
    "pb": 0.20,
    "peer_relative": 0.10,
    "quality_support": 0.10,
}

INVESTED_CAPITAL_METHOD = "equity_plus_debt_minus_cash"
MIN_QUALITY_COMPONENTS = 3
MIN_VALUATION_OBSERVATIONS = 5
