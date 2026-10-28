"""UAG-01 deterministic intent classification — orchestration routing hints only."""

from __future__ import annotations

import re
from typing import Any

from institutional_orchestrator.schema import INTENTS

# Ordered: first match wins for specificity
_INTENT_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Committee", ("committee", "approved", "rejected", "deferred", "escalated", "resolution", "why reduce", "why did the committee")),
    ("Policy", ("policy", "mandate", "violation", "compliance", "constraint", "allowed to")),
    ("Risk", ("portfolio risk", "drawdown", "concentration", "stress", "liquidity", "hhi", "beta")),
    ("Portfolio Analysis", ("portfolio", "holdings", "allocation", "rebalance", "which holdings", "trim", "reduce", "increase cash")),
    ("Observation", ("observation", "what changed", "monitor", "alert", "today")),
    ("Forecast", ("forecast", "scenario", "outlook")),
    ("Comparison", ("compare", "versus", " vs ", "peer")),
    ("Macro", ("macro", "rbi", "inflation", "rates", "gdp")),
    ("Market", ("market", "nifty", "sensex", "sector")),
    ("History", ("history", "timeline", "since", "previously")),
    ("Timeline", ("timeline", "chronolog")),
    ("Research", ("research", "note", "briefing", "memo")),
    ("Company Analysis", ("buy", "sell", "hold", "should i", "thesis", "valuation", "company")),
    ("Search", ("find", "search", "show me", "list")),
)

_TICKER_RE = re.compile(r"\b([A-Z]{2,12}(?:BANK)?)\b")
_KNOWN = {
    "HDFCBANK",
    "ICICIBANK",
    "AXISBANK",
    "KOTAKBANK",
    "RELIANCE",
    "TCS",
    "INFY",
    "SBIN",
    "HDFC",
    "AXIS",
    "ICICI",
    "KOTAK",
}
_ALIASES = {
    "HDFC": "HDFCBANK",
    "AXIS": "AXISBANK",
    "ICICI": "ICICIBANK",
    "KOTAK": "KOTAKBANK",
}


def extract_entities(question: str) -> tuple[str, ...]:
    q = question or ""
    found: list[str] = []
    # Prefer known names case-insensitive
    lower = q.lower()
    for name in sorted(_KNOWN, key=len, reverse=True):
        token = name.replace("BANK", "").lower()
        if name.lower() in lower or (token and token in lower):
            canon = _ALIASES.get(name, name)
            if canon not in found:
                found.append(canon)
    for m in _TICKER_RE.findall(q.upper()):
        canon = _ALIASES.get(m, m)
        if canon in _KNOWN and canon not in found:
            found.append(canon)
    # Phrase hints
    if "hdfc" in lower and "HDFCBANK" not in found:
        found.append("HDFCBANK")
    return tuple(found)


def classify_intent(question: str) -> dict[str, Any]:
    q = (question or "").strip().lower()
    if not q:
        return {"intent": "Search", "confidence": 0, "matched": []}

    # Soft reuse ask_pipeline intent if present
    try:
        from ask_pipeline.intent_resolution import classify_intent as ask_classify  # type: ignore

        soft = ask_classify(question)
        if isinstance(soft, dict) and soft.get("intent"):
            mapped = _map_ask_intent(str(soft.get("intent")))
            if mapped:
                return {
                    "intent": mapped,
                    "confidence": int(soft.get("confidence") or 70),
                    "matched": ["ask_pipeline"],
                    "soft": True,
                }
    except Exception:
        pass

    matched: list[str] = []
    for intent, patterns in _INTENT_PATTERNS:
        for p in patterns:
            if p in q:
                matched.append(p)
                return {
                    "intent": intent,
                    "confidence": 80 if len(p) > 4 else 65,
                    "matched": matched,
                    "soft": False,
                }
    return {"intent": "Company Analysis", "confidence": 40, "matched": [], "soft": False}


def _map_ask_intent(raw: str) -> str | None:
    r = (raw or "").lower()
    mapping = {
        "company": "Company Analysis",
        "portfolio": "Portfolio Analysis",
        "risk": "Risk",
        "policy": "Policy",
        "committee": "Committee",
        "forecast": "Forecast",
        "macro": "Macro",
        "market": "Market",
        "compare": "Comparison",
        "research": "Research",
        "observation": "Observation",
    }
    for k, v in mapping.items():
        if k in r:
            return v
    if raw in INTENTS:
        return raw
    return None
