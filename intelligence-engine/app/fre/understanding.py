"""Step 1 — Query understanding (entities, intent, needs)."""

from __future__ import annotations

import re
from typing import Any

from app.fre.models import QueryUnderstanding

_COMPANY_ALIASES: dict[str, tuple[str, str]] = {
    "reliance": ("Reliance Industries", "RELIANCE"),
    "reliance industries": ("Reliance Industries", "RELIANCE"),
    "ril": ("Reliance Industries", "RELIANCE"),
    "infosys": ("Infosys", "INFY"),
    "infy": ("Infosys", "INFY"),
    "tcs": ("Tata Consultancy Services", "TCS"),
    "hdfc bank": ("HDFC Bank", "HDFCBANK"),
    "hdfcbank": ("HDFC Bank", "HDFCBANK"),
    "bharti": ("Bharti Airtel", "BHARTIARTL"),
    "airtel": ("Bharti Airtel", "BHARTIARTL"),
    "sbi": ("State Bank of India", "SBIN"),
    "itc": ("ITC", "ITC"),
}

_INTENT_RULES: list[tuple[str, list[str]]] = [
    ("investment_analysis", ["should i buy", "should i sell", "buy or sell", "investment case", "worth buying"]),
    ("valuation", ["valuation", "cheap", "expensive", "pe ", "dcf", "fair value"]),
    ("financials", ["revenue", "margin", "eps", "financials", "balance sheet", "cash flow"]),
    ("earnings", ["quarterly", "results", "earnings", "guidance", "transcript"]),
    ("macro", ["macro", "inflation", "rbi", "gdp", "rates", "oil"]),
    ("risk", ["risk", "downside", "threat", "litigation"]),
    ("news", ["latest news", "what happened", "today", "breaking"]),
    ("comparison", ["compare", " versus ", " vs "]),
    ("policy", ["policy", "regulation", "sebi", "gst", "budget"]),
]

_NEED_MAP: dict[str, list[str]] = {
    "investment_analysis": [
        "Financials",
        "Latest News",
        "Quarterly Results",
        "Valuation",
        "Macro",
        "Risks",
    ],
    "valuation": ["Valuation", "Financials", "Peer Comparison", "Analyst Estimates"],
    "financials": ["Financials", "Annual Report", "Quarterly Results"],
    "earnings": ["Quarterly Results", "Conference Call Transcript", "Management Guidance"],
    "macro": ["Macro", "Government Policy", "Rates", "Inflation"],
    "risk": ["Risks", "Exchange Filings", "Latest News"],
    "news": ["Latest News", "Exchange Filings"],
    "comparison": ["Peer Comparison", "Financials", "Valuation"],
    "policy": ["Government Policy", "Regulatory Filings", "Industry Outlook"],
    "general_research": [
        "Annual Report",
        "Quarterly Results",
        "Latest News",
        "Industry Outlook",
    ],
}

_METRIC_RE = re.compile(
    r"\b(revenue|sales|ebitda|pat|profit|margin|eps|roe|roce|pe|pb|debt|cash|guidance|order book)\b",
    re.I,
)
_PERIOD_RE = re.compile(
    r"\b(fy\s?\d{2,4}|q[1-4]\s?fy\s?\d{2,4}|cy\s?\d{4}|20\d{2}|ytd|ttm|last quarter|this year)\b",
    re.I,
)
_COUNTRY_RE = re.compile(r"\b(india|usa|us|china|europe|japan|uk|emerging markets)\b", re.I)
_INDUSTRY_RE = re.compile(
    r"\b(it|banking|pharma|auto|oil|energy|telecom|fmcg|metals|realty|infra|capital goods)\b",
    re.I,
)
_TICKER_RE = re.compile(r"\b([A-Z]{2,12})\b")


def understand_query(query: str, *, aoi: Any | None = None) -> QueryUnderstanding:
    q = (query or "").strip()
    lower = q.lower()
    companies: list[str] = []
    symbols: list[str] = []
    primary = None

    if aoi is not None:
        try:
            co = aoi.registry.resolve(q)
            if co:
                name = getattr(co, "name", None) or getattr(co, "company_name", None)
                sym = getattr(co, "nse_symbol", None)
                if name:
                    companies.append(str(name))
                if sym:
                    symbols.append(str(sym))
                    primary = str(sym)
        except Exception:
            pass

    for alias, (name, sym) in _COMPANY_ALIASES.items():
        if alias in lower:
            if name not in companies:
                companies.append(name)
            if sym not in symbols:
                symbols.append(sym)
            primary = primary or sym

    for tok in _TICKER_RE.findall(q):
        if tok in {"I", "A", "THE", "AND", "OR", "FOR", "TO", "IN", "ON", "OF", "GDP", "RBI", "EPS", "PE"}:
            continue
        if tok not in symbols:
            symbols.append(tok)
            primary = primary or tok

    intents: list[str] = []
    for intent, kws in _INTENT_RULES:
        if any(k in lower for k in kws):
            intents.append(intent)
    if not intents:
        intents = ["general_research"]

    needs: list[str] = []
    for intent in intents:
        for n in _NEED_MAP.get(intent, []):
            if n not in needs:
                needs.append(n)

    return QueryUnderstanding(
        query=q,
        intent=intents[0],
        intents=intents,
        companies=companies,
        symbols=symbols,
        industries=sorted({m.group(0).lower() for m in _INDUSTRY_RE.finditer(q)}),
        countries=sorted({m.group(0).title() for m in _COUNTRY_RE.finditer(q)}),
        metrics=sorted({m.group(0).lower() for m in _METRIC_RE.finditer(q)}),
        time_periods=sorted({m.group(0).upper() for m in _PERIOD_RE.finditer(q)}),
        events=["earnings"] if "earning" in lower or "result" in lower else [],
        needs=needs,
        primary_entity=primary or (companies[0] if companies else None),
    )
