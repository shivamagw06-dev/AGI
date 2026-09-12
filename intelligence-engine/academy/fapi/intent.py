"""Financial intent detection and Academy domain routing for FAPI."""

from __future__ import annotations

import re
from typing import Any


FINANCE_TOKENS = {
    "interest",
    "rate",
    "rates",
    "inflation",
    "gdp",
    "wacc",
    "roic",
    "roe",
    "ebitda",
    "cash",
    "flow",
    "revenue",
    "profit",
    "earnings",
    "valuation",
    "dcf",
    "discount",
    "buyback",
    "buybacks",
    "capital",
    "allocation",
    "margin",
    "working",
    "accrual",
    "accounting",
    "balance",
    "sheet",
    "bank",
    "banks",
    "monetary",
    "fiscal",
    "growth",
    "stock",
    "equity",
    "debt",
    "leverage",
    "npv",
    "intrinsic",
    "forecast",
    "sector",
    "investment",
    "investor",
    "cost",
    "equity",
    "beta",
    "premium",
    "dividend",
    "capex",
    "fcf",
    "fcff",
    "goodwill",
    "impairment",
    "lease",
    "leases",
}

DOMAIN_HINTS: dict[str, tuple[str, ...]] = {
    "economics": (
        "interest",
        "inflation",
        "gdp",
        "monetary",
        "fiscal",
        "recession",
        "unemployment",
        "trade",
        "exchange",
        "money",
        "demand",
        "supply",
        "elasticity",
        "productivity",
        "stagflation",
        "yield",
    ),
    "accounting": (
        "ebitda",
        "cash",
        "accrual",
        "revenue",
        "earnings",
        "working",
        "inventory",
        "receivable",
        "goodwill",
        "impairment",
        "lease",
        "depreciation",
        "accounting",
        "statement",
        "profit",
        "restatement",
        "quality",
    ),
    "corporate_finance": (
        "wacc",
        "roic",
        "buyback",
        "capital",
        "allocation",
        "valuation",
        "dcf",
        "npv",
        "intrinsic",
        "beta",
        "cost of equity",
        "cost of debt",
        "erp",
        "hurdle",
        "leverage",
        "dividend",
        "acquisition",
        "synergy",
        "economic profit",
        "eva",
    ),
}


def detect_finance_intent(query: str) -> dict[str, Any]:
    q = (query or "").strip().lower()
    tokens = set(re.findall(r"[a-z0-9_]+", q))
    finance_hits = sorted(tokens & FINANCE_TOKENS)
    # phrase hints
    phrase_hits = []
    for phrase in ("cost of equity", "cost of capital", "working capital", "interest rate", "free cash"):
        if phrase in q:
            phrase_hits.append(phrase.replace(" ", "_"))
    is_finance = bool(finance_hits or phrase_hits) or bool(
        re.search(r"\b(why|how|should|deserve|valuation|invest)\b", q)
        and re.search(r"\b(company|stock|bank|growth|cash|profit|rate|roic|wacc)\b", q)
    )
    domains: list[str] = []
    for domain, hints in DOMAIN_HINTS.items():
        if any(h in q or h in tokens for h in hints):
            domains.append(domain)
    if is_finance and not domains:
        domains = ["economics", "accounting", "corporate_finance"]
    # multi-discipline synthesis cues
    if any(x in q for x in ("valuation", "invest", "roic", "buy", "deserve")):
        for d in ("economics", "accounting", "corporate_finance"):
            if d not in domains:
                domains.append(d)
    return {
        "is_finance": bool(is_finance),
        "domains": domains,
        "token_hits": finance_hits,
        "phrase_hits": phrase_hits,
        "require_academy": bool(is_finance),
    }
