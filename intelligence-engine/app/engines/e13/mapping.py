"""E13 P0 fundamental metric map and Feature Registry bindings."""

from __future__ import annotations

MODEL_VERSION = "e13-p0-fundamental-0.1.0"
ENGINE_VERSION = "1.0.0"
FORMULA_ID = "FM_AGI_FUND"

# P0 score pillars
P0_PILLARS: tuple[str, ...] = ("QUALITY", "VALUE", "GROWTH", "BALANCE_SHEET")

METRIC_KEYS: tuple[str, ...] = (
    "revenue_growth",
    "eps_growth",
    "gross_margin",
    "oper_margin",
    "net_margin",
    "roe",
    "roic",
    "roce",
    "leverage",
    "debt_equity",
    "interest_coverage",
    "accruals",
    "fcf_yield",
    "fcf_conversion",
    "earn_stability",
    "ep_ttm",
    "bp",
    "ev_ebitda_inv",
    "sp",
    "peg",
)

REGISTRY_TO_METRIC: dict[str, str] = {
    "FUND_ROE": "roe",
    "FUND_ROIC": "roic",
    "FUND_ROCE": "roce",
    "FUND_GROSS_MARGIN": "gross_margin",
    "FUND_OPERATING_MARGIN": "oper_margin",
    "FUND_NET_MARGIN": "net_margin",
    "FUND_REVENUE_GROWTH": "revenue_growth",
    "FUND_EPS_GROWTH": "eps_growth",
    "FUND_DEBT_EQUITY": "debt_equity",
    "FUND_INTEREST_COVERAGE": "interest_coverage",
    "FUND_FCF_YIELD": "fcf_yield",
    "FUND_FCF_CONVERSION": "fcf_conversion",
    "FUND_PEG": "peg",
    "FUND_EP": "ep_ttm",
    "FUND_BP": "bp",
}

# Pillar → (metric, weight, invert?)
PILLAR_WEIGHTS: dict[str, list[tuple[str, float, bool]]] = {
    "GROWTH": [
        ("revenue_growth", 0.55, False),
        ("eps_growth", 0.45, False),
    ],
    "QUALITY": [
        ("roe", 0.20, False),
        ("roic", 0.20, False),
        ("roce", 0.15, False),
        ("gross_margin", 0.10, False),
        ("oper_margin", 0.10, False),
        ("net_margin", 0.10, False),
        ("earn_stability", 0.10, False),
        ("accruals", 0.05, True),
    ],
    "BALANCE_SHEET": [
        ("leverage", 0.30, True),
        ("debt_equity", 0.30, True),
        ("interest_coverage", 0.25, False),
        ("fcf_conversion", 0.15, False),
    ],
    "VALUE": [
        ("ep_ttm", 0.25, False),
        ("ev_ebitda_inv", 0.20, False),
        ("fcf_yield", 0.20, False),
        ("bp", 0.15, False),
        ("sp", 0.10, False),
        ("peg", 0.10, True),  # lower PEG better
    ],
}

COMPOSITE_WEIGHTS: dict[str, float] = {
    "QUALITY": 0.35,
    "VALUE": 0.30,
    "GROWTH": 0.20,
    "BALANCE_SHEET": 0.15,
}
