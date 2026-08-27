"""Historical intent detection and period extraction.

Two jobs: decide whether a question is asking about history at all, and work out
*which* history it is asking about. The second matters as much as the first —
"since 2005" and "over the last three years" both route here, but only one of
them is answerable from a three-year series, and the span guard cannot tell the
difference unless the asked period is extracted.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

# Words that make a question historical. Ordered roughly by how unambiguous they are.
HISTORICAL_MARKERS = (
    "historical", "historically", "history", "over time", "evolution", "evolved",
    "trend", "trended", "trajectory", "since", "during", "through", "before",
    "after", "previous", "past", "used to", "back then", "all time", "all-time",
    "ever", "longest", "cheapest", "dearest", "highest", "lowest", "peak",
    "trough", "compare over", "last decade", "decade", "years ago", "changed over",
)

# Named periods a desk actually refers to. Ranges are deliberately generous at the
# edges: "during COVID" means the episode, not a precise trading window.
NAMED_PERIODS: dict[str, tuple[str, str, str]] = {
    "covid": ("2020-02-01", "2021-06-30", "the COVID period"),
    "pandemic": ("2020-02-01", "2021-06-30", "the pandemic"),
    "gfc": ("2008-01-01", "2009-06-30", "the global financial crisis"),
    "financial crisis": ("2008-01-01", "2009-06-30", "the global financial crisis"),
    "global financial crisis": ("2008-01-01", "2009-06-30", "the global financial crisis"),
    "2008 crisis": ("2008-01-01", "2009-06-30", "the 2008 crisis"),
    "demonetisation": ("2016-11-01", "2017-03-31", "demonetisation"),
    "demonetization": ("2016-11-01", "2017-03-31", "demonetisation"),
    "taper tantrum": ("2013-05-01", "2013-12-31", "the taper tantrum"),
    "dot com": ("1999-01-01", "2002-12-31", "the dot-com cycle"),
    "dotcom": ("1999-01-01", "2002-12-31", "the dot-com cycle"),
}

# Question shape to metric. First match wins, so the specific sits above the generic.
METRIC_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"price[- ]to[- ]book|p/?b\b|price/book", "pb"),
    (r"price[- ]to[- ]earnings|p/?e\b(?! ratio band)|earnings multiple", "pe"),
    (r"ev/?ebitda|enterprise value to ebitda", "ev_ebitda"),
    (r"ev/?sales", "ev_sales"),
    (r"price/?sales|p/?s\b", "price_sales"),
    (r"dividend yield", "dividend_yield"),
    (r"market cap|mcap|market capitalisation|market capitalization", "market_cap"),
    (r"\broe\b|return on equity", "roe"),
    (r"\broce\b|return on capital", "roce"),
    (r"net margin|profit margin", "net_margin"),
    (r"ebitda margin|operating margin", "ebitda_margin"),
    (r"debt[- ]to[- ]equity|debt/equity|leverage|gearing", "debt_equity"),
    (r"free cash flow|\bfcf\b", "free_cash_flow"),
    (r"\bebitda\b", "ebitda"),
    (r"revenue|sales|topline|top line", "revenue"),
    (r"\beps\b|earnings per share", "eps"),
    (r"profit|\bpat\b|net income|earnings\b", "pat"),
    (r"\bdebt\b|borrowing", "debt"),
    (r"\bcash\b", "cash"),
    (r"promoter", "promoter_holding"),
    (r"\bfii\b|foreign holding", "fii"),
    (r"target price|consensus target", "target_price"),
    (r"valuation|multiple|expensive|cheap|rerat|re-rat", "pe"),
    (r"share price|stock price|\bprice\b|returns?\b", "price"),
)

# Which module should answer, by question shape.
_EXTREME = re.compile(r"cheapest|dearest|most expensive|highest|lowest|peak|trough|best|worst|"
                      r"all[- ]time|ever\b", re.IGNORECASE)
_COMPARE = re.compile(r"\bcompare\b|\bversus\b|\bvs\.?\b|against\b|relative to\b", re.IGNORECASE)
# "relative to its own history" compares a company with its past, not with a peer.
_SELF_RELATIVE = re.compile(r"(relative to|against|versus|vs\.?)\s+(its|their|his|her|the company\'s)?"
                            r"\s*(own\s+)?(history|past|record|average|median|range)",
                            re.IGNORECASE)
_EVENTS = re.compile(r"event|dividend|split|bonus|buyback|merger|acquisition|timeline|"
                     r"what happened|announcement", re.IGNORECASE)
_TREND = re.compile(r"trend|growth|grew|evolution|evolved|changed over|improve|deteriorat|"
                    r"acceleration|since|over the (last|past)", re.IGNORECASE)


def is_historical(question: str) -> bool:
    text = (question or "").lower()
    if any(marker in text for marker in HISTORICAL_MARKERS):
        return True
    # "in 2019", "in FY18" — a bare past year is a historical question.
    return bool(re.search(r"\b(?:in|for)\s+(?:fy\s?\d{2}|19\d{2}|20[0-2]\d)\b", text))


def extract_metric(question: str) -> str:
    text = (question or "").lower()
    for pattern, metric in METRIC_PATTERNS:
        if re.search(pattern, text):
            return metric
    return "price"


def extract_period(question: str, *, today: Optional[date] = None) -> dict[str, Any]:
    """The window the question asks about, and how it was expressed."""
    text = (question or "").lower()
    now = today or datetime.now(timezone.utc).date()

    for token, (start, end, label) in NAMED_PERIODS.items():
        if token in text:
            return {"start": start, "end": end, "label": label, "kind": "named",
                    "asked": True}

    since = re.search(r"since\s+(?:fy\s?)?(\d{4}|\d{2})\b", text)
    if since:
        raw = since.group(1)
        year = int(raw) if len(raw) == 4 else 2000 + int(raw)
        return {"start": f"{year}-01-01", "end": now.isoformat(),
                "label": f"since {year}", "kind": "since", "asked": True}

    span = re.search(r"(?:last|past)\s+(\d{1,2}|two|three|five|ten|twenty)\s*(year|decade)", text)
    if span:
        words = {"two": 2, "three": 3, "five": 5, "ten": 10, "twenty": 20}
        raw = span.group(1)
        count = words.get(raw, int(raw) if raw.isdigit() else 1)
        if span.group(2) == "decade":
            count *= 10
        start = now - timedelta(days=int(365.25 * count))
        return {"start": start.isoformat(), "end": now.isoformat(),
                "label": f"the last {count} years", "kind": "rolling", "asked": True}

    if "decade" in text:
        start = now - timedelta(days=3652)
        return {"start": start.isoformat(), "end": now.isoformat(),
                "label": "the last decade", "kind": "rolling", "asked": True}

    year = re.search(r"\b(?:in|for|during)\s+(19\d{2}|20[0-2]\d)\b", text)
    if year:
        value = year.group(1)
        return {"start": f"{value}-01-01", "end": f"{value}-12-31",
                "label": f"in {value}", "kind": "year", "asked": True}

    if re.search(r"all[- ]time|ever\b|since listing|full history|entire history", text):
        return {"start": None, "end": now.isoformat(), "label": "its full history",
                "kind": "all_time", "asked": True}

    # No explicit period: the question is historical in shape but open ended.
    return {"start": None, "end": now.isoformat(), "label": "the observed history",
            "kind": "open", "asked": False}


def classify(question: str) -> dict[str, Any]:
    """Route a historical question to the module that should answer it."""
    text = question or ""
    if _COMPARE.search(text) and not _SELF_RELATIVE.search(text):
        module = "comparison"
    elif _EXTREME.search(text):
        module = "valuation_extreme"
    elif _EVENTS.search(text):
        module = "events"
    elif _TREND.search(text):
        module = "trend"
    else:
        module = "trend"

    metric = extract_metric(text)
    # An extreme asked of a non-valuation metric is still a series extreme.
    if module == "valuation_extreme" and metric not in (
        "pe", "pb", "ev_ebitda", "ev_sales", "price_sales", "dividend_yield", "market_cap", "price"
    ):
        module = "trend_extreme"

    return {
        "historical": is_historical(text),
        "module": module,
        "metric": metric,
        "period": extract_period(text),
        "symbols": extract_symbols(text),
    }


_STOPWORDS = {
    "SHOW", "WHEN", "WHAT", "HOW", "WHY", "WAS", "WERE", "HAS", "HAVE", "DID", "DOES",
    "THE", "AND", "FOR", "OVER", "SINCE", "DURING", "BEFORE", "AFTER", "COMPARE", "VS",
    "VERSUS", "FROM", "WITH", "THIS", "THAT", "ITS", "HIS", "HER", "PAST", "LAST",
    "YEARS", "YEAR", "DECADE", "HISTORY", "HISTORICAL", "TREND", "GROWTH", "EVER",
    "CHEAPEST", "HIGHEST", "LOWEST", "PEAK", "COVID", "GFC", "AGIB", "AGI",
}


def extract_symbols(question: str) -> list[str]:
    """Uppercase tokens that look like tickers. The caller resolves names properly."""
    out: list[str] = []
    for token in re.findall(r"\b[A-Z][A-Z0-9&._-]{2,}\b", question or ""):
        if token in _STOPWORDS or token in out:
            continue
        out.append(token)
    return out
