"""Production research label bands — unchanged thresholds (spec §16.3)."""

from __future__ import annotations


def category(score: float) -> str:
    """Exact production `category()` from nifty500_research_engine.py."""
    if score >= 72:
        return "Strong Bullish"
    if score >= 58:
        return "Bullish"
    if score >= 43:
        return "Neutral"
    if score >= 28:
        return "Bearish"
    return "Strong Bearish"
