"""E02 P0 factor map and Feature Registry metric bindings."""

from __future__ import annotations

MODEL_VERSION = "e02-p0-factors-0.1.0"
ENGINE_VERSION = "1.0.0"

# P0 factors only
P0_FACTORS: tuple[str, ...] = (
    "F_MOMENTUM",
    "F_LOWVOL",
    "F_SIZE",
    "F_LIQUIDITY",
    "F_QUALITY",
    "F_VALUE",
)

# Canonical intermediate feature ids (Factor Feature Builder outputs)
FACTOR_FEATURE_IDS: dict[str, str] = {
    "F_MOMENTUM": "FACTOR_MOMENTUM",
    "F_LOWVOL": "FACTOR_LOWVOL",
    "F_SIZE": "FACTOR_SIZE",
    "F_LIQUIDITY": "FACTOR_LIQUIDITY",
    "F_QUALITY": "FACTOR_QUALITY",
    "F_VALUE": "FACTOR_VALUE",
}

# Metric keys used in panels (from FeatureSnapshot / registry)
METRIC_KEYS: tuple[str, ...] = (
    "ret_12_1",
    "ret_6_1",
    "ret_3_0",
    "beta",
    "sigma_60",
    "rv_20",
    "log_mcap",
    "mcap",
    "adv_value_20d",
    "amihud_60d",
    "float_share",
    "turnover_20d",
    "roe",
    "roic",
    "gross_margin",
    "oper_margin",
    "accruals",
    "leverage",
    "earn_stability",
    "ep_ttm",
    "bp",
    "ev_ebitda_inv",
    "fcf_yield",
    "sp",
)

# Feature Registry → metric
REGISTRY_TO_METRIC: dict[str, str] = {
    "FUND_ROE": "roe",
    "FUND_ROIC": "roic",
    "FUND_GROSS_MARGIN": "gross_margin",
    "FUND_OPERATING_MARGIN": "oper_margin",
    "VOL_REALIZED_20": "rv_20",
    "TECH_ATR_14": "sigma_60",  # proxy when sigma_60 absent
}

# Factor → (metric, weight, invert?)
# invert=True means lower raw is better → use -z
FACTOR_WEIGHTS: dict[str, list[tuple[str, float, bool]]] = {
    "F_MOMENTUM": [
        ("ret_12_1", 0.60, False),
        ("ret_6_1", 0.25, False),
        ("ret_3_0", 0.15, False),
    ],
    "F_LOWVOL": [
        ("beta", 0.50, True),
        ("sigma_60", 0.50, True),
    ],
    "F_SIZE": [
        ("log_mcap", 1.00, True),  # small = high score
    ],
    "F_LIQUIDITY": [
        ("adv_value_20d", 0.40, False),
        ("amihud_60d", 0.30, True),
        ("float_share", 0.30, False),
    ],
    "F_QUALITY": [
        ("roe", 0.20, False),
        ("roic", 0.20, False),
        ("gross_margin", 0.10, False),
        ("oper_margin", 0.10, False),
        ("accruals", 0.15, True),
        ("leverage", 0.15, True),
        ("earn_stability", 0.10, False),
    ],
    "F_VALUE": [
        ("ep_ttm", 0.25, False),
        ("ev_ebitda_inv", 0.25, False),
        ("fcf_yield", 0.20, False),
        ("bp", 0.15, False),
        ("sp", 0.15, False),
    ],
}

# Norm mode: sector or universe
FACTOR_NORM: dict[str, str] = {
    "F_MOMENTUM": "universe",
    "F_LOWVOL": "sector",
    "F_SIZE": "universe",
    "F_LIQUIDITY": "universe",
    "F_QUALITY": "sector",
    "F_VALUE": "sector",
}
