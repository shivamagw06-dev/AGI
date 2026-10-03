"""Step 1 — Intent detection (deterministic lexicon)."""

from __future__ import annotations

import re

from app.irp.models import IntentType


_RULES: list[tuple[IntentType, tuple[str, ...]]] = [
    ("compare_companies", ("compare", " vs ", "versus", "relative to", "peer")),
    ("valuation", ("valuation", "fair value", "multiple", "target price", "pe ratio", "p/e")),
    ("risk_analysis", ("risk", "downside", "drawdown", "tail risk", "what can go wrong")),
    ("earnings_analysis", ("earnings", "results", "quarterly", "q1", "q2", "q3", "q4", "guidance")),
    ("prediction", ("predict", "prediction", "forecast accuracy", "house view accuracy")),
    ("portfolio_construction", ("portfolio", "allocate", "position size", "construct a book")),
    ("event_impact", ("event impact", "what happens if", "rate cut impact", "fed decision")),
    ("market_outlook", ("market outlook", "nifty", "sensex", "market view", "index outlook")),
    ("investment_thesis", ("investment thesis", "house view", "agi view", "your view", "stance")),
    ("macro_research", ("macro", "inflation", "rates", "gdp", "rbi", "fed", "currency", "fx")),
    ("theme_research", ("theme", "ai adoption", "china plus one", "digital banking", "ev transition")),
    ("sector_research", ("sector", "services doing", "industry", "how is indian", "how are indian")),
    ("company_research", ("should i buy", "stock", "company", "ticker")),
    ("screening", ("screen", "filter stocks", "shortlist", "ideas in")),
    ("news_explanation", ("explain this news", "what does this mean", "headline")),
    ("general_finance_education", ("what is a", "explain pe", "how does", "definition")),
]


def detect_intent(question: str) -> IntentType:
    q = (question or "").lower().strip()
    if not q:
        return "general_research"
    # Sector shorthand: "how is X doing" without a single ticker often = sector
    if re.search(r"\bhow (is|are)\b.+\b(doing|performing|faring)\b", q) and any(
        tok in q for tok in ("sector", "services", "banks", "it ", " indian", "india ")
    ):
        return "sector_research"
    for intent, keys in _RULES:
        if any(k in q for k in keys):
            return intent
    return "general_research"
