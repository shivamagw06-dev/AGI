"""Macro feature mapping: Feature Registry IDs → E01 feature_ids (P0)."""

from __future__ import annotations

# Feature Registry → E01 FeatureVector keys (frozen P0 mapping)
REGISTRY_TO_E01: dict[str, str] = {
    "MACRO_YIELD_CURVE_10Y2Y": "yc_slope_us",
    "MACRO_DOLLAR_STRENGTH": "usd_mom_63d",
    "MACRO_OIL_MOMENTUM": "oil_mom_63d",
    "VOL_REALIZED_20": "rv_equity_20d",
}

# Canonical E01 feature ids used by threshold classifiers (spec §6)
E01_FEATURE_IDS: tuple[str, ...] = (
    "yc_slope_us",
    "yc_inversion_us",
    "real_yield_us",
    "infl_yoy_us",
    "infl_momentum_us",
    "pmi_us",
    "pmi_in",
    "pmi_momentum_us",
    "growth_impulse",
    "oil_mom_63d",
    "gold_mom_63d",
    "copper_mom_63d",
    "usd_mom_63d",
    "usd_strength",
    "liq_trend",
    "policy_rate_us",
    "policy_velocity_us",
    "vix_level",
    "vix_pctile_5y",
    "india_vix_level",
    "rv_equity_20d",
    "hy_oas",
    "credit_stress",
    "risk_appetite",
    "stress_index",
    "earn_density",
    "rate_real_impulse",
)

# Required for P0 threshold axes — missing → stale_inputs
P0_REQUIRED_FEATURES: tuple[str, ...] = (
    "pmi_us",
    "pmi_in",
    "growth_impulse",
    "infl_momentum_us",
    "liq_trend",
    "vix_pctile_5y",
    "risk_appetite",
    "stress_index",
    "yc_slope_us",
    "usd_mom_63d",
    "oil_mom_63d",
    "hy_oas",
)

MODEL_VERSION = "e01-p0-axes-0.1.0"
ENGINE_VERSION = "1.0.0"
