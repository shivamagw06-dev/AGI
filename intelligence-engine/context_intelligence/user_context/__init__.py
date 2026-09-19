"""Detect user intent mode: research / decision / learning / monitoring."""

from __future__ import annotations

from typing import Any


def detect_user_context(
    question: str,
    *,
    primary_objective: str | None = None,
    question_type: str | None = None,
    decision_type: str | None = None,
    research_depth: str | None = None,
) -> dict[str, Any]:
    mode = "Research"
    if question_type in {"Should I Buy?", "Should I Sell?"} or primary_objective == "Investment Evaluation":
        mode = "Investment Decision"
    elif question_type in {"Explain", "Teach"} or primary_objective == "Educational":
        mode = "Learning"
    elif question_type == "Monitor" or research_depth == "Continuous Monitoring":
        mode = "Monitoring"
    elif primary_objective == "Portfolio Decision" or question_type == "Rebalance":
        mode = "Portfolio Review"
    elif research_depth in {"Institutional", "Deep Research"}:
        mode = "Institutional"
    elif primary_objective == "Educational":
        mode = "Educational"

    return {
        "mode": mode,
        "decision_type": decision_type or ("Investment" if mode == "Investment Decision" else "Research"),
        "research_depth": research_depth or "Standard",
        "institutional": mode in {"Investment Decision", "Institutional", "Portfolio Review"},
        "confidence": 0.95,
    }
