"""CAE query classification and context planning."""

from __future__ import annotations

import re
from typing import Any

from app.cae.config import INTENT_ENGINES, INTENT_KEYWORDS, INTENT_LABELS
from app.cae.models import QueryPlan, new_id

_TICKER_RE = re.compile(r"\b([A-Z]{2,12})\b")
_STOP = {
    "I",
    "A",
    "AN",
    "THE",
    "AND",
    "OR",
    "FOR",
    "TO",
    "IN",
    "ON",
    "OF",
    "IS",
    "IT",
    "VS",
    "CEO",
    "GDP",
    "RBI",
    "USD",
    "INR",
    "EPS",
    "PAT",
    "ROE",
    "PE",
    "AI",
    "EV",
    "WHAT",
    "DID",
    "SAY",
    "ABOUT",
    "SUMMARIZE",
    "SUMMARISE",
    "EXPLAIN",
    "COMPARE",
    "CAPEX",
    "MID",
    "YEAR",
    "EQUITY",
    "OUTLOOK",
    "INDIA",
    "MODEL",
    "BUSINESS",
}


def classify_intents(query: str) -> list[str]:
    q = (query or "").lower()
    hits: list[str] = []
    for intent, kws in INTENT_KEYWORDS.items():
        if any(k in q for k in kws):
            hits.append(intent)
    if "should i buy" in q or "should i sell" in q:
        for extra in ("company_research", "investment_thesis", "forecast", "risk"):
            if extra not in hits:
                hits.append(extra)
    if " vs " in q or " versus " in q or "compare" in q:
        if "comparison" not in hits:
            hits.append("comparison")
    if not hits:
        hits = ["mixed_intent"]
    # preserve order, valid labels only
    out = []
    for h in hits:
        if h in INTENT_LABELS and h not in out:
            out.append(h)
    if len(out) > 1 and "mixed_intent" not in out:
        out.append("mixed_intent")
    return out


def extract_entities(query: str, *, ticker: str | None = None, aoi: Any | None = None) -> tuple[list[str], str | None]:
    from app.kip.extractors import looks_like_equity_ticker

    entities: list[str] = []
    primary = str(ticker).upper() if ticker and looks_like_equity_ticker(str(ticker)) else None
    if aoi is not None:
        try:
            co = aoi.registry.resolve(query)
            if co:
                sym = co.nse_symbol or co.company_id
                if sym and looks_like_equity_ticker(str(sym)):
                    primary = primary or str(sym).upper()
                    if co.nse_symbol and looks_like_equity_ticker(str(co.nse_symbol)):
                        entities.append(str(co.nse_symbol).upper())
                    if co.company_id and str(co.company_id).upper() not in entities and looks_like_equity_ticker(
                        str(co.company_id)
                    ):
                        entities.append(str(co.company_id).upper())
        except Exception:
            pass
    # Only accept uppercase tokens that look like real equity tickers — never prose verbs.
    for tok in _TICKER_RE.findall((query or "").upper()):
        if tok in _STOP or not looks_like_equity_ticker(tok):
            continue
        if tok not in entities:
            entities.append(tok)
        if primary is None:
            primary = tok
    # comparison second ticker
    lower = (query or "").lower()
    if " vs " in lower or " versus " in lower:
        parts = re.split(r"\bvs\b|\bversus\b", query, flags=re.I)
        for part in parts[1:]:
            for tok in _TICKER_RE.findall(part.upper()):
                if tok not in _STOP and looks_like_equity_ticker(tok) and tok not in entities:
                    entities.append(tok)
    return entities[:8], primary


def plan_query(query: str, *, ticker: str | None = None, aoi: Any | None = None) -> QueryPlan:
    intents = classify_intents(query)
    entities, primary = extract_entities(query, ticker=ticker, aoi=aoi)
    engines: list[str] = []
    for intent in intents:
        for eng in INTENT_ENGINES.get(intent, []):
            if eng not in engines:
                engines.append(eng)
    if not engines:
        engines = list(INTENT_ENGINES["mixed_intent"])

    expand = any(i in intents for i in ("company_research", "investment_thesis", "macro_analysis", "comparison"))
    strategy = "balanced_institutional"
    if "forecast" in intents:
        strategy = "forecast_aware"
    if "risk" in intents:
        strategy = "risk_first"
    if "event" in intents or "news" in intents:
        strategy = "event_driven"
    if "comparison" in intents:
        strategy = "comparative"

    return QueryPlan(
        plan_id=new_id("plan"),
        query=query,
        intents=intents,
        entities=entities,
        primary_ticker=primary,
        engines=engines,
        expand_relationships=expand,
        reasoning_strategy=strategy,
    )
