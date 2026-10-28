"""What is already priced in / street expectations."""

from __future__ import annotations

import re
from typing import Any


def detect_expectation_context(
    question: str,
    *,
    primary_objective: str | None = None,
    entity_type: str | None = None,
) -> dict[str, Any]:
    text = question or ""
    cues = []
    if re.search(r"\b(priced\s+in|consensus|street|guidance)\b", text, re.I):
        cues.append("Street Expectations")
    if re.search(r"\b(ai\s+optimism|optimism|pessimism)\b", text, re.I):
        cues.append("Sentiment")
    if primary_objective == "Investment Evaluation":
        summary = "High quality already priced in"
        cues = cues or ["Street Expectations", "Historical Average", "AGIB View"]
    elif primary_objective == "Historical Analysis":
        summary = "AI optimism" if re.search(r"\b(it|tech|ai)\b", text, re.I) else "Mean-reversion expectations"
        cues = ["Historical Average", "Street Expectations", "AGIB View"]
    elif primary_objective == "Educational":
        summary = "Not applicable"
        cues = []
    else:
        summary = "Consensus vs AGIB view"
        cues = cues or ["Consensus", "AGIB View"]

    return {
        "priced_in": summary,
        "street_expectations": "Consensus" in cues or "Street Expectations" in cues,
        "management_guidance": bool(re.search(r"\bguidance\b", text, re.I)),
        "consensus": True if cues else False,
        "historical_average": "Historical Average" in cues,
        "agib_view": "AGIB View" in cues,
        "cues": cues,
        "summary": summary,
        "required": bool(cues),
        "confidence": 0.9 if cues else 0.75,
    }
