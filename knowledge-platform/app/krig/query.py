"""Lightweight query intent classification for KRIG (no LLM)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.krig.policies import QueryType

COMPARE_RE = re.compile(
    r"\b(compare|vs\.?|versus|against)\b",
    re.IGNORECASE,
)
SECTOR_HINTS = (
    "sector",
    "industry",
    "it services",
    "banking",
    "banks",
    "pharma",
    "auto",
    "fmcg",
    "metal",
    "energy",
)
MACRO_HINTS = (
    "rbi",
    "repo rate",
    "inflation",
    "gdp",
    "macro",
    "rate cut",
    "rate hike",
    "monetary policy",
    "fiscal",
    "cpi",
)
MARKET_HINTS = ("nifty", "bank nifty", "sensex", "market regime", "breadth", "india market")
PORTFOLIO_HINTS = ("portfolio", "thesis", "should i invest", "position", "allocation", "idea")

TICKER_RE = re.compile(r"\b([A-Z]{2,12})\b")
KNOWN = {
    "INFY",
    "TCS",
    "WIPRO",
    "HCLTECH",
    "TECHM",
    "RELIANCE",
    "HDFCBANK",
    "ICICIBANK",
    "KOTAKBANK",
    "AXISBANK",
    "SBIN",
    "ITC",
    "HDFC",
}


SECTOR_ALIASES = {
    "banking": "financials",
    "banks": "financials",
    "bank": "financials",
    "it": "technology",
    "it services": "technology",
    "tech": "technology",
    "technology": "technology",
    "auto": "consumer_cyclical",
    "pharma": "healthcare",
}


@dataclass
class KnowledgeQuery:
    query_type: QueryType
    question: str | None = None
    symbols: list[str] = field(default_factory=list)
    sector_key: str | None = None
    market_key: str = "india_equity"
    sections: list[str] | None = None


def classify_query(
    *,
    question: str | None = None,
    symbols: list[str] | None = None,
    sector_key: str | None = None,
    query_type: str | None = None,
) -> KnowledgeQuery:
    if query_type:
        qt = QueryType(query_type)
        return KnowledgeQuery(
            query_type=qt,
            question=question,
            symbols=[s.upper() for s in (symbols or [])],
            sector_key=sector_key,
        )

    q = question or ""
    found = [s.upper() for s in (symbols or [])]
    for m in TICKER_RE.findall(q.upper()):
        if m in KNOWN and m not in found:
            found.append(m)
    # Common spoken names
    lower = q.lower()
    if "infosys" in lower and "INFY" not in found:
        found.append("INFY")
    if "hdfc bank" in lower and "HDFCBANK" not in found:
        found.append("HDFCBANK")
    if "icici" in lower and "ICICIBANK" not in found:
        found.append("ICICIBANK")

    if COMPARE_RE.search(q) and len(found) >= 2:
        return KnowledgeQuery(query_type=QueryType.COMPARE, question=q, symbols=found[:4])

    if any(h in lower for h in MACRO_HINTS):
        return KnowledgeQuery(query_type=QueryType.MACRO, question=q, symbols=found, market_key="india_equity")

    if any(h in lower for h in MARKET_HINTS):
        return KnowledgeQuery(query_type=QueryType.MARKET, question=q, symbols=found)

    for alias, key in SECTOR_ALIASES.items():
        if alias in lower:
            return KnowledgeQuery(query_type=QueryType.SECTOR, question=q, sector_key=key, symbols=found)

    if any(h in lower for h in SECTOR_HINTS) and not found:
        return KnowledgeQuery(query_type=QueryType.SECTOR, question=q, sector_key=sector_key or "technology")

    if any(h in lower for h in PORTFOLIO_HINTS) and found:
        return KnowledgeQuery(query_type=QueryType.PORTFOLIO, question=q, symbols=found[:1])

    if found:
        return KnowledgeQuery(query_type=QueryType.COMPANY, question=q, symbols=found[:1])

    return KnowledgeQuery(query_type=QueryType.MACRO, question=q, market_key="india_equity")
