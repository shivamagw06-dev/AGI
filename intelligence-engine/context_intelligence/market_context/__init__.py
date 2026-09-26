"""Infer market regime / cycle cues from question + objective."""

from __future__ import annotations

import re
from typing import Any


def detect_market_context(
    question: str,
    *,
    primary_objective: str | None = None,
    entity_type: str | None = None,
    sector: str | None = None,
) -> dict[str, Any]:
    text = question or ""
    regime = "Neutral"
    conf = 0.82
    notes: list[str] = []

    if re.search(r"\b(bear\s+market|crash|sell[- ]off)\b", text, re.I):
        regime, conf = "Bear Market", 0.95
    elif re.search(r"\b(bull\s+market|rally|melt[- ]up)\b", text, re.I):
        regime, conf = "Bull Market", 0.95
    elif re.search(r"\b(correction)\b", text, re.I):
        regime, conf = "Correction", 0.94
    elif re.search(r"\b(recovery|rebound)\b", text, re.I):
        regime, conf = "Recovery", 0.93
    elif re.search(r"\b(high\s+volatility|volatile|vix)\b", text, re.I):
        regime, conf = "High Volatility", 0.93
    elif re.search(r"\b(low\s+volatility|calm\s+markets?)\b", text, re.I):
        regime, conf = "Low Volatility", 0.92
    elif primary_objective == "Historical Analysis":
        regime, conf = "Recovery", 0.86
        it_cue = ("IT" in str(sector or "").upper()) or ("IT" in text.upper())
        notes.append("IT recovery cycle" if it_cue else "Mean-reversion backdrop")
    elif primary_objective == "Investment Evaluation":
        regime, conf = "Late-cycle expansion", 0.88
        if sector and "bank" in str(sector).lower():
            notes.append("Bullish Financial Sector")
        else:
            notes.append("Constructive equity regime")
    elif primary_objective == "Macro Impact":
        regime, conf = "Neutral", 0.85
        notes.append("Policy-sensitive regime")

    liquidity = "Normal"
    if re.search(r"\b(liquidity\s+crunch|tight\s+liquidity)\b", text, re.I):
        liquidity = "Tight"
    elif re.search(r"\b(ample\s+liquidity|excess\s+liquidity)\b", text, re.I):
        liquidity = "Ample"

    return {
        "regime": regime,
        "market_regime": regime,
        "liquidity_conditions": liquidity,
        "rate_cycle": "Moderately restrictive" if primary_objective in {"Investment Evaluation", "Macro Impact"} else "Neutral",
        "inflation_cycle": "Cooling" if primary_objective in {"Investment Evaluation", "Macro Impact"} else "Stable",
        "credit_cycle": "Stable",
        "notes": notes,
        "summary": notes[0] if notes else regime,
        "confidence": conf,
        "required": True,
    }
