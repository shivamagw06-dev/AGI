"""E09 P0 CTA trend metric map and Feature Registry bindings."""

from __future__ import annotations

MODEL_VERSION = "e09-p0-cta-trend-0.1.0"
ENGINE_VERSION = "1.0.0"
FORMULA_ID = "TM_AGI_CTA"

HORIZONS: tuple[str, ...] = ("short", "medium", "long")

METRIC_KEYS: tuple[str, ...] = (
    "ret_short",
    "ret_medium",
    "ret_long",
    "roc_10",
    "ema_12",
    "ema_26",
    "adx_14",
    "rsi_14",
    "realized_vol_20",
    "ts_momentum",
    "vol_scaled_signal",
    "persistence",
    "exhaustion",
)

REGISTRY_TO_METRIC: dict[str, str] = {
    "TECH_ROC_10": "roc_10",
    "TECH_EMA_12": "ema_12",
    "TECH_EMA_26": "ema_26",
    "TECH_ADX_14": "adx_14",
    "TECH_RSI_14": "rsi_14",
    "VOL_REALIZED_20": "realized_vol_20",
}

# Panel aliases from shared golden / e02 panels
PANEL_ALIASES: dict[str, str] = {
    "ret_3_0": "ret_short",
    "ret_6_1": "ret_medium",
    "ret_12_1": "ret_long",
    "sigma_60": "realized_vol_20",
    "rv_20": "realized_vol_20",
}
