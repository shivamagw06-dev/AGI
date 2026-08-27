"""S02 — Intent detection (integration classifier; does not replace evidence contracts)."""

from __future__ import annotations

import re
from typing import Any

from ask_pipeline.schema import INTENT_TO_QUESTION_TYPE, INTENTS


def detect_intent(question: str) -> dict[str, Any]:
    q = str(question or "").strip()
    ql = q.lower()
    if not ql:
        return {
            "intent": "Unknown",
            "confidence": 0.2,
            "reasons": ["empty_question"],
            "question_type_hint": "valuation",
        }

    # Domain intents first (higher priority than Education catch-alls).
    rules: list[tuple[str, tuple[str, ...], float]] = [
        ("Replay", ("replay", "point-in-time", "as of date", "as-of"), 0.9),
        ("Historical", ("historically", "history of", "over the last", "past 10 years", "time series", "historical pe", "last decade"), 0.9),
        ("Portfolio", ("portfolio", "position size", "allocation", "weight", "exposure"), 0.9),
        ("Risk", ("drawdown", "var ", "volatility", "downside", "risk of"), 0.86),
        ("Comparison", ("compare", " vs ", "versus", "relative to"), 0.9),
        ("AlternativeData", ("alternative data", "satellite", "card spend", "web traffic", "app download", "pmi"), 0.92),
        ("Expectation", ("expectation gap", "consensus", "guidance", "surprise", "estimate revision", "beat", "miss"), 0.9),
        ("Government", ("rbi", "sebi", "gst", "budget", "pli", "government", "policy", "regulation"), 0.9),
        ("Industry", ("value chain", "industry", "sector structure", "supply chain"), 0.9),
        ("Macro", ("macro", "inflation", "gdp", "interest rate", "fed", "yield curve"), 0.88),
        ("Accounting", ("accounting", "earnings quality", "accrual", "cash conversion", "balance sheet"), 0.9),
        ("BusinessQuality", ("business quality", "moat", "roic", "franchise", "capital allocation", "quality business"), 0.9),
        ("Valuation", ("valu", "fair value", "dcf", "pe ratio", "multiple", "expensive", "cheap", "overvalued", "undervalued"), 0.88),
        ("Watchlist", ("watchlist", "watch list", "monitor"), 0.84),
        ("Screening", ("screen", "screener", "filter stocks", "universe filter"), 0.84),
        ("Research", ("research", "analyse", "analyze", "thesis", "deep dive"), 0.7),
    ]

    invest = bool(
        re.search(
            r"\b(should i invest|should we invest|invest [£$€₹]|buy |sell |recommend)\b",
            ql,
        )
    )

    best: tuple[str, float, str] | None = None
    for intent, keys, score in rules:
        hit = next((k for k in keys if k in ql), None)
        if hit:
            if best is None or score > best[1]:
                best = (intent, score, f"matched:{hit}")

    # Education only when definitional AND no stronger domain match
    education_shape = bool(
        re.search(r"^(what is|what's|define|explain|meaning of)\b", ql)
        or ("what is a " in ql)
        or ("what does " in ql and " mean" in ql)
    )
    # Allow education for pure concept asks even mid-sentence
    pure_education = education_shape and not best
    soft_education = (
        any(k in ql for k in ("what is", "define ", "meaning of"))
        and best is None
    )

    has_entity_cue = bool(
        re.search(
            r"\b(infosys|tcs|reliance|hdfc|wipro|nifty|apple|microsoft)\b",
            ql,
        )
        or " vs " in ql
        or "versus" in ql
        or re.search(r"\bfor\s+[a-z]{3,}\b", ql)
    )

    if invest:
        intent = "Portfolio"
        conf = 0.93
        reasons = ["investment_recommendation_language"]
        if best:
            reasons.append(f"also:{best[0]}")
    elif education_shape and not has_entity_cue and (
        best is None
        or best[0]
        in {"Valuation", "Accounting", "BusinessQuality", "Risk", "Macro", "Research"}
    ):
        intent, conf, reasons = "Education", 0.93, ["definition_shape_no_entity"]
    elif best:
        intent, conf, reason = best
        reasons = [reason]
    elif pure_education or soft_education:
        intent, conf, reasons = "Education", 0.92, ["definition_shape"]
    else:
        intent, conf, reasons = "Unknown", 0.45, ["no_strong_pattern"]

    if intent not in INTENTS:
        intent = "Unknown"

    return {
        "intent": intent,
        "confidence": conf,
        "reasons": reasons,
        "question_type_hint": INTENT_TO_QUESTION_TYPE.get(intent, "valuation"),
        "investment_recommendation": invest,
    }
