"""Question type, decision type, depth, urgency, expected output."""

from __future__ import annotations

import re
from typing import Any

_BUY = re.compile(r"\b(should\s+i\s+buy|buy\s+|worth\s+buying|accumulate|invest\s+in)\b", re.I)
_SELL = re.compile(r"\b(should\s+i\s+sell|exit|trim|book\s+profits?)\b", re.I)
_COMPARE = re.compile(
    r"\b(compare)\b|\bvs\.?\b|\bversus\b(?!\s+history)",
    re.I,
)
_EXPLAIN = re.compile(r"\b(explain|what\s+is|define|meaning)\b", re.I)
_TEACH = re.compile(r"\b(teach|tutorial|learn|how\s+does\s+.+\s+work)\b", re.I)
_FORECAST = re.compile(r"\b(forecast|predict|outlook|next\s+(year|quarter))\b", re.I)
_SUM = re.compile(r"\b(summarise|summarize|summary|brief\s+me)\b", re.I)
_SCREEN = re.compile(r"\b(screen|screener|filter\s+stocks|find\s+stocks)\b", re.I)
_MONITOR = re.compile(r"\b(monitor|track|watch|alert)\b", re.I)
_STRESS = re.compile(r"\b(stress\s+test|shock|tail\s+risk)\b", re.I)
_REBAL = re.compile(r"\b(rebalance|reallocation)\b", re.I)
_REVIEW = re.compile(r"\b(review|assess|evaluate)\b", re.I)
_AUDIT = re.compile(r"\b(audit|forensic|accounting\s+review)\b", re.I)
_DIAG = re.compile(r"\b(diagnose|what\s+is\s+wrong|root\s+cause)\b", re.I)
_ANALYSE = re.compile(r"\b(analyse|analyze|analysis|deep\s+dive)\b", re.I)

_LIVE = re.compile(r"\b(live|right\s+now|intraday|today\s+morning)\b", re.I)
_TODAY = re.compile(r"\b(today|this\s+session|eod)\b", re.I)
_NEAR = re.compile(r"\b(this\s+week|near\s+term|next\s+month|short\s+term)\b", re.I)
_LONG = re.compile(r"\b(long\s+term|multi[- ]year|5[- ]year|decade)\b", re.I)

_QUICK = re.compile(r"\b(quick|tl;dr|briefly|in\s+one\s+line)\b", re.I)
_DEEP = re.compile(r"\b(deep\s+research|exhaustive|comprehensive|full\s+diligence)\b", re.I)
_CONT = re.compile(r"\b(continuous|ongoing|monitor|track)\b", re.I)
_INST = re.compile(r"\b(institutional|committee|ic\s+memo|investment\s+committee)\b", re.I)


def classify_question_meta(
    question: str,
    *,
    primary_objective: str | None,
) -> dict[str, Any]:
    text = question or ""
    qtype = "Analyse"
    if _BUY.search(text):
        qtype = "Should I Buy?"
    elif _SELL.search(text):
        qtype = "Should I Sell?"
    elif _COMPARE.search(text):
        qtype = "Compare"
    elif _TEACH.search(text):
        qtype = "Teach"
    elif _EXPLAIN.search(text):
        qtype = "Explain"
    elif _FORECAST.search(text):
        qtype = "Forecast"
    elif _SUM.search(text):
        qtype = "Summarise"
    elif _SCREEN.search(text):
        qtype = "Screen"
    elif _STRESS.search(text):
        qtype = "Stress Test"
    elif _REBAL.search(text):
        qtype = "Rebalance"
    elif _MONITOR.search(text):
        qtype = "Monitor"
    elif _AUDIT.search(text):
        qtype = "Audit"
    elif _DIAG.search(text):
        qtype = "Diagnose"
    elif _REVIEW.search(text):
        qtype = "Review"
    elif _ANALYSE.search(text):
        qtype = "Analyse"

    decision = "Company"
    if primary_objective == "Educational":
        decision = "Educational"
    elif primary_objective in {"Macro Impact", "Policy Analysis", "Regulatory Analysis"}:
        decision = "Macro"
    elif primary_objective in {"Portfolio Decision"}:
        decision = "Portfolio"
    elif primary_objective in {"Sector Attractiveness", "Industry Structure", "Historical Analysis"}:
        decision = "Sector" if re.search(r"\b(sector|nifty|industry)\b", text, re.I) else "Company"
    elif primary_objective == "Screening":
        decision = "Operational"
    elif qtype in {"Should I Buy?", "Should I Sell?"}:
        decision = "Investment"
    elif primary_objective == "Investment Evaluation":
        decision = "Investment"

    if _LIVE.search(text):
        urgency = "Live"
    elif _TODAY.search(text):
        urgency = "Today"
    elif _NEAR.search(text):
        urgency = "Near Term"
    elif _LONG.search(text):
        urgency = "Long Term"
    elif primary_objective == "Educational":
        urgency = "Evergreen"
    else:
        urgency = "Near Term"

    if _CONT.search(text) or qtype == "Monitor":
        depth = "Continuous Monitoring"
    elif _DEEP.search(text):
        depth = "Deep Research"
    elif _QUICK.search(text) or qtype == "Summarise":
        depth = "Quick"
    elif _INST.search(text) or primary_objective == "Investment Evaluation" or qtype == "Should I Buy?":
        depth = "Institutional"
    elif primary_objective == "Educational":
        depth = "Standard"
    else:
        depth = "Standard"

    expected = _expected_output(primary_objective, qtype, depth)
    return {
        "question_type": qtype,
        "decision_type": decision,
        "research_depth": depth,
        "urgency": urgency,
        "expected_output": expected,
    }


def _expected_output(primary: str | None, qtype: str, depth: str) -> str:
    if primary == "Educational" or qtype in {"Explain", "Teach"}:
        return "Educational Guide"
    if primary == "Peer Comparison" or qtype == "Compare":
        return "Comparison Report"
    if primary == "Historical Analysis":
        return "Valuation Report"
    if primary == "Macro Impact":
        return "Macro Report"
    if primary == "Portfolio Decision" or qtype == "Rebalance":
        return "Portfolio Memo"
    if primary == "Scenario Analysis":
        return "Scenario Report"
    if primary == "Forecast" or qtype == "Forecast":
        return "Forecast Report"
    if primary == "Risk Assessment" or qtype == "Stress Test":
        return "Risk Report"
    if primary == "Screening" or qtype == "Screen":
        return "Screening Report"
    if primary == "Investment Evaluation" or qtype in {"Should I Buy?", "Should I Sell?"}:
        if depth in {"Institutional", "Deep Research"}:
            return "Institutional Report"
        return "Research Note"
    if depth == "Quick" or qtype == "Summarise":
        return "Brief"
    if depth == "Institutional":
        return "Committee Memo"
    return "Research Note"
