"""Scenario backdrop: normal / stress / recovery / etc."""

from __future__ import annotations

import re
from typing import Any

_MAP: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(stress\s+test|crisis|tail\s+risk)\b", re.I), "Stress"),
    (re.compile(r"\b(recession|depression)\b", re.I), "Recession"),
    (re.compile(r"\b(recovery)\b", re.I), "Recovery"),
    (re.compile(r"\b(expansion|boom)\b", re.I), "Expansion"),
    (re.compile(r"\b(high\s+inflation|stagflation)\b", re.I), "High Inflation"),
    (re.compile(r"\b(rate\s+cuts?)\b", re.I), "Rate Cuts"),
    (re.compile(r"\b(bear\s+case|bull\s+case|scenario)\b", re.I), "Scenario Set"),
]


def detect_scenario_context(
    question: str,
    *,
    primary_objective: str | None = None,
) -> dict[str, Any]:
    text = question or ""
    for pat, name in _MAP:
        if pat.search(text):
            return {"scenario": name, "required": True, "confidence": 0.95}
    if primary_objective == "Scenario Analysis":
        return {"scenario": "Scenario Set", "required": True, "confidence": 0.96}
    if primary_objective == "Risk Assessment":
        return {"scenario": "Stress", "required": True, "confidence": 0.9}
    if primary_objective == "Macro Impact" and re.search(r"\brate\s+cut", text, re.I):
        return {"scenario": "Rate Cuts", "required": True, "confidence": 0.96}
    return {"scenario": "Normal", "required": True, "confidence": 0.9}
