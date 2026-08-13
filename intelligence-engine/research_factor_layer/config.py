"""Versioned factor methodologies. Weights live here, never in UI code."""

QUALITY_VERSION = "quality-compounder-v2.0.0"
EARNINGS_QUALITY_VERSION = "earnings-quality-v1.0.0"
SUSTAINABLE_GROWTH_VERSION = "sustainable-growth-v1.0.0"
CAPITAL_ALLOCATION_VERSION = "capital-allocation-v1.0.0"
BALANCE_SHEET_RISK_VERSION = "balance-sheet-risk-v1.0.0"
MISPRICING_VERSION = "relative-mispricing-v1.0.0"

QUALITY_WEIGHTS = {"roic_quality": .25, "roic_stability": .15, "fcf_quality": .15,
                   "growth_quality": .15, "margin_quality": .10, "reinvestment_efficiency": .10,
                   "balance_sheet_quality": .10}
EARNINGS_QUALITY_WEIGHTS = {"cash_conversion": .25, "working_capital_quality": .20,
                            "fcf_conversion": .20, "exceptional_quality": .15, "accrual_quality": .20}
SUSTAINABLE_GROWTH_WEIGHTS = {"growth": .25, "sustainable_growth": .25, "margin_change": .15,
                              "internal_funding": .20, "capital_efficiency": .15}
CAPITAL_ALLOCATION_WEIGHTS = {"reinvestment_returns": .30, "cash_discipline": .20,
                              "acquisition_discipline": .15, "shareholder_distribution": .15,
                              "debt_discipline": .20}
BALANCE_SHEET_RISK_WEIGHTS = {"leverage": .25, "coverage": .20, "cash_debt": .10, "cfo_debt": .10,
                              "liabilities_equity": .10, "working_capital_risk": .15, "asset_risk": .10}

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
