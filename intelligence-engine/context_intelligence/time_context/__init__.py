"""Detect institutional time horizon from the question."""

from __future__ import annotations

import re
from typing import Any

_PATTERNS: list[tuple[re.Pattern[str], str, float]] = [
    (re.compile(r"\b(intraday|right\s+now|this\s+session|live\s+tape)\b", re.I), "Intraday", 0.98),
    (re.compile(r"\b(today|what\s+happened\s+today|eod)\b", re.I), "Today", 0.99),
    (re.compile(r"\b(this\s+week|near\s+term|next\s+few\s+days)\b", re.I), "This Week", 0.96),
    (re.compile(r"\b(this\s+quarter|q[1-4]|next\s+quarter)\b", re.I), "Quarter", 0.96),
    (re.compile(r"\b(this\s+year|fy2[0-9]|next\s+12\s+months|1[- ]year)\b", re.I), "Year", 0.95),
    (re.compile(r"\b(5[- ]years?|five\s+years?)\b", re.I), "5 Years", 0.99),
    (re.compile(r"\b(10[- ]years?|ten\s+years?|decade)\b", re.I), "10 Years", 0.99),
    (re.compile(r"\b(long[- ]term|multi[- ]year|for\s+the\s+long\s+run|invest\s+for)\b", re.I), "Long Term", 0.97),
]


def detect_time_context(question: str, *, primary_objective: str | None = None) -> dict[str, Any]:
    text = question or ""
    for pat, horizon, conf in _PATTERNS:
        if pat.search(text):
            return {
                "time_horizon": horizon,
                "framework": _framework(horizon),
                "confidence": conf,
                "required": True,
            }
    # Defaults by objective
    if primary_objective == "Educational":
        horizon, conf = "Evergreen", 0.9
    elif primary_objective in {"News Impact", "Event Analysis"}:
        horizon, conf = "Today", 0.88
    elif primary_objective == "Historical Analysis":
        horizon, conf = "10 Years", 0.9
    elif primary_objective in {"Investment Evaluation", "Portfolio Decision"}:
        horizon, conf = "Long Term", 0.92
    else:
        horizon, conf = "Year", 0.8
    return {
        "time_horizon": horizon if horizon != "Evergreen" else "Long Term",
        "framework": _framework(horizon if horizon != "Evergreen" else "Long Term"),
        "confidence": conf,
        "required": True,
        "evergreen": horizon == "Evergreen",
    }


def _framework(horizon: str) -> str:
    if horizon in {"Intraday", "Today"}:
        return "Intraday framework"
    if horizon in {"This Week", "Quarter"}:
        return "Near-term framework"
    if horizon in {"5 Years", "10 Years", "Long Term"}:
        return "Long-term framework"
    return "Standard framework"
