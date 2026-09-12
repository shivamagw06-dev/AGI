"""E03 P0 constants."""

from __future__ import annotations

MODEL_VERSION = "e03-sm-agi-tech-0.1.0"
ENGINE_VERSION = "1.0.0"
SUBMODEL_ID = "SM_AGI_TECH"
ALPHA_ID = "A_AGI_TECH"

# Production CONFIG mirrors (nifty500_research_engine.py)
RSI_PERIOD = 14
SMA_SHORT = 20
SMA_LONG = 50
SMA_200 = 200
VOLUME_AVERAGE_PERIOD = 20
MIN_BARS = SMA_200

INDICATOR_KEYS: tuple[str, ...] = (
    "rsi",
    "macd_histogram",
    "macd_positive",
    "above_sma20",
    "above_sma50",
    "above_sma200",
    "sma20_above_sma50",
    "percent_b",
    "atr_percent",
    "volume_ratio",
    "change_5d",
    "change_20d",
    "change_60d",
    "roc_10",
    "position_52w",
)
