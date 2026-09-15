"""Detect whether portfolio context must be attached."""

from __future__ import annotations

import re
from typing import Any


def detect_portfolio_context(
    question: str,
    *,
    primary_objective: str | None = None,
    question_type: str | None = None,
) -> dict[str, Any]:
    text = question or ""
    explicit = bool(
        re.search(
            r"\b(portfolio|allocation|rebalance|position\s+sizing|holdings?|"
            r"diversif|risk\s+budget|₹|build\s+a\s+.+\s+portfolio)\b",
            text,
            re.I,
        )
    )
    required = (
        explicit
        or primary_objective == "Portfolio Decision"
        or question_type in {"Rebalance", "Should I Buy?", "Should I Sell?"}
        or primary_objective == "Investment Evaluation"
    )
    # Educational / pure historical index questions: not required
    if primary_objective == "Educational":
        required = False
    if primary_objective == "Historical Analysis" and not explicit:
        required = False

    attachments = []
    if required:
        attachments = [
            "Current Holdings",
            "Sector Exposure",
            "Country Exposure",
            "Factor Exposure",
            "Diversification",
            "Cash Position",
            "Risk Budget",
        ]
    return {
        "required": required,
        "attachments": attachments,
        "summary": "Required" if required else "Not Required",
        "confidence": 0.99 if explicit or primary_objective == "Portfolio Decision" else (0.95 if required else 0.97),
    }
