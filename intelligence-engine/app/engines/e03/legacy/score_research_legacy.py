"""Legacy production reference — byte-identical logic to nifty500_research_engine.py.

Kept separate from SM_AGI_TECH so parity audit can run both sides.
Do not diverge from production without an architecture change.
"""

from __future__ import annotations

from typing import Any


def score_research_legacy(indicators: dict[str, Any]) -> float:
    """AGI research score, derived from trend, momentum, participation and structure."""
    score = 50.0
    rsi = indicators["rsi"]
    score += 8 if rsi >= 60 else 3 if rsi >= 50 else -3 if rsi <= 40 else 0
    score += (
        7
        if indicators["macd_positive"] and indicators["macd_histogram"] > 0
        else -7
        if not indicators["macd_positive"] and indicators["macd_histogram"] < 0
        else 0
    )
    score += sum(
        (3 if flag else -3)
        for flag in (
            indicators["above_sma20"],
            indicators["above_sma50"],
            indicators["above_sma200"],
        )
    )
    score += 5 if indicators["sma20_above_sma50"] else -5
    score += 5 if indicators["change_20d"] > 2 else -5 if indicators["change_20d"] < -2 else 0
    score += 5 if indicators["change_60d"] > 5 else -5 if indicators["change_60d"] < -5 else 0
    score += (
        4
        if indicators["volume_ratio"] >= 1.2 and indicators["change_5d"] > 0
        else -4
        if indicators["volume_ratio"] >= 1.2 and indicators["change_5d"] < 0
        else 0
    )
    score += 5 if indicators["position_52w"] >= 0.7 else -5 if indicators["position_52w"] <= 0.3 else 0
    score += 3 if indicators["roc_10"] > 0 else -3 if indicators["roc_10"] < 0 else 0
    return round(max(0, min(100, score)), 1)


def category_legacy(score: float) -> str:
    if score >= 72:
        return "Strong Bullish"
    if score >= 58:
        return "Bullish"
    if score >= 43:
        return "Neutral"
    if score >= 28:
        return "Bearish"
    return "Strong Bearish"


def confidence_legacy(score: float, indicators: dict[str, Any]) -> int:
    direction = score >= 50
    checks = [
        indicators["rsi"] >= 50,
        indicators["macd_histogram"] > 0,
        indicators["above_sma50"],
        indicators["above_sma200"],
        indicators["change_20d"] > 0,
        indicators["change_60d"] > 0,
        indicators["position_52w"] >= 0.5,
    ]
    agreement = sum(check == direction for check in checks) / len(checks)
    return round(min(95, max(40, (50 + abs(score - 50)) * (0.7 + agreement * 0.3))))
