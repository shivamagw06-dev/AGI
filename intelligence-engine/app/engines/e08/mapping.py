"""E08 P0 volatility metric map and Feature Registry bindings."""

from __future__ import annotations

MODEL_VERSION = "e08-p0-volatility-0.1.0"
ENGINE_VERSION = "1.0.0"
FORMULA_ID = "VM_AGI_VOL"

REGIMES: tuple[str, ...] = ("compression", "normal", "expansion", "extreme")

METRIC_KEYS: tuple[str, ...] = (
    "realized_vol_20",
    "hist_vol_60",
    "atr_14",
    "iv_rank",
    "expected_move",
    "vol_ratio",
    "expansion_score",
    "compression_score",
)

REGISTRY_TO_METRIC: dict[str, str] = {
    "VOL_REALIZED_20": "realized_vol_20",
    "VOL_HIST_60": "hist_vol_60",
    "VOL_ATR_14": "atr_14",
    "OPTIONS_IV_RANK": "iv_rank",
}
