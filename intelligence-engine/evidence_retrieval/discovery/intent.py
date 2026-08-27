"""Deterministic discovery — intent, entities, evidence types from a question."""

from __future__ import annotations

import re
from typing import Any

from evidence_retrieval.schema import EVIDENCE_TYPES

_TICKER = re.compile(r"\b([A-Z]{2,12})(?:\.(?:NS|BO))?\b")
_KNOWN = {
    "INFY",
    "TCS",
    "RELIANCE",
    "HDFCBANK",
    "WIPRO",
    "INFOSYS",
    "TATA",
}
_ALIAS = {"INFOSYS": "INFY", "TATA": "TCS"}

_KEYWORDS: list[tuple[str, list[str], list[str]]] = [
    ("macro", ["repo", "inflation", "cpi", "gdp", "rbi", "liquidity", "interest rate", "macro"], ["MACRO_INDICATORS"]),
    ("government", ["sebi", "policy", "gst", "budget", "regulation", "government", "pli"], ["GOVERNMENT_POLICIES"]),
    ("industry", ["industry", "sector", "value chain", "competition", "peers"], ["RELATIONSHIP_GRAPH"]),
    ("alt_data", ["upi", "gst collection", "iip", "power demand", "alternative data"], ["ALTERNATIVE_DATA"]),
    ("events", ["dividend", "buyback", "merger", "announcement", "board meeting", "split", "bonus"], ["CORPORATE_EVENTS", "TIMELINES"]),
    ("documents", ["annual report", "transcript", "presentation", "md&a", "risk factor", "filing", "notes to"], ["DOCUMENT_SECTIONS", "RISK_FACTORS", "MANAGEMENT_COMMENTARY", "CONFERENCE_CALLS", "INVESTOR_PRESENTATIONS", "ACCOUNTING_NOTES"]),
    ("ownership", ["shareholding", "promoter", "ownership", "pledged"], ["OWNERSHIP"]),
    ("valuation", ["valuation", "pe ", "p/e", "ev/ebitda", "historical valuation"], ["HISTORICAL_VALUATION", "FINANCIAL_METRICS"]),
    ("financials", ["revenue", "margin", "earnings", "profit", "financial", "roic", "cash flow"], ["FINANCIAL_METRICS"]),
]


def discover(question: str, *, ticker_hint: str | None = None, as_of: str | None = None) -> dict[str, Any]:
    q = (question or "").strip()
    ql = q.lower()
    companies: list[str] = []
    if ticker_hint:
        companies.append(str(ticker_hint).upper())
    for m in _TICKER.findall(q.upper()):
        if m in _KNOWN or len(m) <= 10:
            companies.append(_ALIAS.get(m, m))
    # alias words
    for word, tick in (("infosys", "INFY"), ("reliance", "RELIANCE"), ("hdfc bank", "HDFCBANK"), ("wipro", "WIPRO")):
        if word in ql and tick not in companies:
            companies.append(tick)
    # dedupe preserve order
    seen = set()
    companies = [c for c in companies if not (c in seen or seen.add(c))]  # type: ignore[func-returns-value]
    companies = [c for c in companies if c in _KNOWN or c in _ALIAS.values() or (ticker_hint and c == ticker_hint.upper())]

    topics: list[str] = []
    evidence_needed: list[str] = []
    for topic, keys, types in _KEYWORDS:
        if any(k in ql for k in keys):
            topics.append(topic)
            evidence_needed.extend(types)
    if not topics:
        topics = ["company"]
        evidence_needed = ["FINANCIAL_METRICS", "CORPORATE_EVENTS", "DOCUMENT_SECTIONS"]
    if companies and "company" not in topics:
        topics.insert(0, "company")

    # document type hint
    doc_type = None
    for label, key in (
        ("ANNUAL_REPORT", "annual report"),
        ("QUARTERLY_REPORT", "quarterly"),
        ("INVESTOR_PRESENTATION", "presentation"),
        ("CONFERENCE_CALL_TRANSCRIPT", "transcript"),
        ("EXCHANGE_FILING", "filing"),
    ):
        if key in ql:
            doc_type = label
            break

    # historical date hint YYYY-MM-DD or FY
    date_match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", q)
    fy_match = re.search(r"\bfy\s?(20\d{2}|2\d)\b", ql)
    historical_date = date_match.group(1) if date_match else None
    if not historical_date and fy_match:
        historical_date = None  # FY alone is not as_of

    evidence_needed = [e for e in dict.fromkeys(evidence_needed) if e in EVIDENCE_TYPES]
    return {
        "question": q,
        "companies": companies,
        "sectors": ["IT"] if any(c in {"INFY", "TCS", "WIPRO"} for c in companies) else [],
        "industries": ["Information Technology"] if any(c in {"INFY", "TCS", "WIPRO"} for c in companies) else [],
        "topics": topics,
        "macro_topic": "monetary_policy" if "macro" in topics else None,
        "government_policy": "sebi_or_budget" if "government" in topics else None,
        "economic_theme": topics[0] if topics else None,
        "document_type": doc_type,
        "historical_date": historical_date,
        "as_of": as_of or historical_date,
        "portfolio_context": "portfolio" in ql or "holding" in ql,
        "evidence_types_required": evidence_needed,
        "fabricated": False,
    }
