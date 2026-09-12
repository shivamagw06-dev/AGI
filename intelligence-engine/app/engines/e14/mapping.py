"""E14 feature mapping — Feature Registry + E01 bridge (P0)."""

from __future__ import annotations

MODEL_VERSION = "e14-p0-rules-0.1.0"
ENGINE_VERSION = "1.0.0"

TAXONOMY_IDS: tuple[str, ...] = (
    "RK_MARKET",
    "RK_LIQUIDITY",
    "RK_CREDIT",
    "RK_VOL",
    "RK_CORR",
    "RK_TAIL",
    "RK_GAP",
    "RK_FACTOR",
    "RK_CROWD",
    "RK_EXEC",
    "RK_MACRO",
    "RK_EVENT",
    "RK_GEO",
    "RK_FX",
    "RK_REG",
    "RK_CONC",
    "RK_DD",
    "RK_SYSTEMIC",
)

# Feature Registry → E14 risk feature ids
REGISTRY_TO_E14: dict[str, str] = {
    "MACRO_YIELD_CURVE_10Y2Y": "yc_slope_us",
    "MACRO_DOLLAR_STRENGTH": "usd_mom_63d",
    "MACRO_OIL_MOMENTUM": "oil_mom_63d",
    "VOL_REALIZED_20": "rv_equity_20d",
}

# Direct E14 / book feature ids accepted from FeatureSnapshot
E14_FEATURE_IDS: tuple[str, ...] = (
    "vix_pctile_5y",
    "india_vix_pctile_5y",
    "rv_ratio_20_60",
    "corr_avg_20d",
    "corr_spike",
    "liquidity_index",
    "days_to_exit_stress",
    "crowding_index",
    "fragility_index",
    "tail_risk_score",
    "name_hhi",
    "sector_hhi",
    "portfolio_beta",
    "stress_worst_pnl",
    "macro_risk_bridge",
    "exec_impact_bps",
    "expected_dd_3m_p95",
    "hy_oas",
    "credit_stress",
    "gap_buffer_mult",
    "herding_agib",
    "pct_adv_proposed",
    "yc_slope_us",
    "usd_mom_63d",
    "oil_mom_63d",
    "rv_equity_20d",
    "gross",
    "net",
)

P0_REQUIRED_FEATURES: tuple[str, ...] = (
    "vix_pctile_5y",
    "liquidity_index",
    "crowding_index",
    "fragility_index",
    "tail_risk_score",
    "corr_avg_20d",
    "macro_risk_bridge",
)
