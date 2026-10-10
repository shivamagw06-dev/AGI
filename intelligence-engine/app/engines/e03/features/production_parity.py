"""Production indicator formulas — parity port of calculate_indicators().

Uses the same pandas rolling/ewm definitions as nifty500_research_engine.py.
Never calls MarketDataClient; operates on OHLCV already present in FeatureSnapshot.
"""

from __future__ import annotations

import math
from typing import Any, Optional

import pandas as pd

from app.engines.e03.mapping import (
    MIN_BARS,
    RSI_PERIOD,
    SMA_200,
    VOLUME_AVERAGE_PERIOD,
)


def last_or_default(series: pd.Series, default: float = 0.0) -> float:
    value = series.iloc[-1] if len(series) else default
    return float(value) if pd.notna(value) else default


def calculate_indicators(frame: pd.DataFrame) -> Optional[dict[str, Any]]:
    """Exact production calculate_indicators — requires ≥200 bars."""
    if len(frame) < MIN_BARS:
        return None

    close, high, low, volume = frame["close"], frame["high"], frame["low"], frame["volume"]
    delta = close.diff()
    gain, loss = delta.clip(lower=0), -delta.clip(upper=0)
    average_gain = gain.ewm(com=RSI_PERIOD - 1, min_periods=RSI_PERIOD).mean()
    average_loss = loss.ewm(com=RSI_PERIOD - 1, min_periods=RSI_PERIOD).mean()
    rsi = 100 - (100 / (1 + average_gain / average_loss.replace(0, math.nan)))

    ema_fast = close.ewm(span=12, adjust=False).mean()
    ema_slow = close.ewm(span=26, adjust=False).mean()
    macd = ema_fast - ema_slow
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    histogram = macd - macd_signal

    sma20, sma50, sma200 = close.rolling(20).mean(), close.rolling(50).mean(), close.rolling(SMA_200).mean()
    middle = close.rolling(20).mean()
    std = close.rolling(20).std()
    upper, lower = middle + 2 * std, middle - 2 * std
    band_width = upper - lower
    percent_b = (close - lower) / band_width.replace(0, math.nan)

    previous_close = close.shift()
    true_range = pd.concat(
        [high - low, (high - previous_close).abs(), (low - previous_close).abs()],
        axis=1,
    ).max(axis=1)
    atr = true_range.ewm(com=13, min_periods=14).mean()

    average_volume = volume.rolling(VOLUME_AVERAGE_PERIOD).mean()
    roc_10 = (close / close.shift(10) - 1) * 100
    change_5 = (close / close.shift(5) - 1) * 100
    change_20 = (close / close.shift(20) - 1) * 100
    change_60 = (close / close.shift(60) - 1) * 100

    high_52 = high.rolling(252).max()
    low_52 = low.rolling(252).min()
    position_52 = (close - low_52) / (high_52 - low_52).replace(0, math.nan)

    return {
        "rsi": last_or_default(rsi, 50),
        "macd_histogram": last_or_default(histogram),
        "macd_positive": last_or_default(macd) > last_or_default(macd_signal),
        "above_sma20": last_or_default(close) > last_or_default(sma20),
        "above_sma50": last_or_default(close) > last_or_default(sma50),
        "above_sma200": last_or_default(close) > last_or_default(sma200),
        "sma20_above_sma50": last_or_default(sma20) > last_or_default(sma50),
        "percent_b": last_or_default(percent_b, 0.5),
        "atr_percent": (last_or_default(atr) / max(last_or_default(close), 0.01)) * 100,
        "volume_ratio": last_or_default(volume) / max(last_or_default(average_volume, 1), 1),
        "change_5d": last_or_default(change_5),
        "change_20d": last_or_default(change_20),
        "change_60d": last_or_default(change_60),
        "roc_10": last_or_default(roc_10),
        "position_52w": last_or_default(position_52, 0.5),
    }


def frame_from_bars(bars: list[dict[str, Any]]) -> pd.DataFrame:
    """Build OHLCV frame from FeatureSnapshot metadata bars."""
    rows = []
    for b in bars:
        rows.append(
            {
                "close": float(b["close"]),
                "high": float(b.get("high", b["close"])),
                "low": float(b.get("low", b["close"])),
                "volume": float(b.get("volume", 0.0)),
            }
        )
    return pd.DataFrame(rows)
