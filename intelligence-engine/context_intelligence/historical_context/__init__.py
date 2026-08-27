"""Attach historical series / valuation context requirements."""

from __future__ import annotations

import re
from typing import Any


def detect_historical_context(
    question: str,
    *,
    primary_objective: str | None = None,
) -> dict[str, Any]:
    text = question or ""
    hist_cue = bool(
        re.search(
            r"\b(versus\s+history|vs\s+history|historical|historically|"
            r"5[- ]year|10[- ]year|percentile|mean\s+reversion)\b",
            text,
            re.I,
        )
    )
    required = hist_cue or primary_objective in {
        "Historical Analysis",
        "Valuation Assessment",
        "Investment Evaluation",
        "Peer Comparison",
    }
    series = []
    if required:
        series = [
            "5 Year Trend",
            "10 Year Trend",
            "Historical Valuation",
            "Historical ROE",
            "Historical Growth",
            "Historical Risks",
        ]
        if primary_objective == "Historical Analysis":
            series = [
                "Historical PE",
                "Historical PB",
                "10 Year Trend",
                "Historical Valuation",
                "Historical Forecast Accuracy",
            ]
    summary = None
    if primary_objective == "Investment Evaluation":
        summary = "Trading near historical valuation range"
    elif primary_objective == "Historical Analysis":
        summary = "Historical multiples comparison required"

    return {
        "required": required,
        "series": series,
        "summary": summary,
        "confidence": 0.96 if hist_cue or primary_objective == "Historical Analysis" else (0.9 if required else 0.7),
    }
