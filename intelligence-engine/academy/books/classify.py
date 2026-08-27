"""Classify concepts into Academy taxonomy (domain + sector academies)."""

from __future__ import annotations

from academy.books.schema import ACADEMY_TAXONOMY


_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("accounting", ("accounting", "accrual", "revenue recognition", "balance sheet", "income statement", "audit", "impairment", "goodwill", "depreciation")),
    ("valuation", ("valuation", "dcf", "wacc", "capm", "multiple", "intrinsic", "terminal value", "peg", "ev/ebitda", "price to")),
    ("corporate_finance", ("capital allocation", "leverage", "buyback", "dividend", "cost of capital", "roic", "wacc", "m&a", "payout")),
    ("economics", ("supply", "demand", "elasticity", "gdp", "inflation", "monetary", "fiscal", "opportunity cost")),
    ("behavioural_finance", ("behaviour", "bias", "anchoring", "herding", "prospect", "overconfidence", "loss aversion")),
    ("risk_management", ("risk", "volatility", "drawdown", "var", "hedge", "crowding", "liquidity risk")),
    ("portfolio_management", ("portfolio", "allocation", "diversification", "sharpe", "factor", "rebalance")),
    ("macro", ("macro", "rates", "currency", "commodity cycle", "regime", "central bank")),
    ("sector_banking", ("bank", "nim", "casa", "npa", "cet1", "credit cost")),
    ("sector_it_services", ("it services", "software services", "deal wins", "utilisation", "offshore")),
    ("sector_fmcg", ("fmcg", "staples", "brand power", "pricing power", "distribution")),
    ("sector_pharma", ("pharma", "drug", "anda", "pipeline", "usfda")),
    ("sector_insurance", ("insurance", "combined ratio", "float", "underwriting")),
    ("sector_energy", ("oil", "gas", "refining", "upstream", "power")),
    ("sector_infrastructure", ("infrastructure", "concession", "toll", "epc")),
    ("sector_real_estate", ("real estate", "pre-sales", "rera", "nav")),
    ("sector_telecom", ("telecom", "arpu", "spectrum", "subscriber")),
    ("sector_automobiles", ("auto", "automobile", "ev", "dealer", "asp")),
    ("sector_metals", ("steel", "metal", "aluminium", "copper", "mining")),
    ("sector_capital_goods", ("capital goods", "industrial", "machinery", "order book")),
    ("sector_chemicals", ("chemical", "specialty chemical", "petrochemical")),
    ("sector_consumer_durables", ("durable", "appliance", "consumer electronics")),
    ("investment", ("invest", "moat", "margin of safety", "compound", "quality", "growth", "value")),
]


def classify_academy(text: str) -> str:
    blob = (text or "").lower()
    best = "investment"
    score = 0
    for academy, keys in _RULES:
        s = sum(1 for k in keys if k in blob)
        if s > score:
            score = s
            best = academy
    return best if best in ACADEMY_TAXONOMY else "investment"


def classify_many(texts: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for t in texts:
        a = classify_academy(t)
        counts[a] = counts.get(a, 0) + 1
    return counts
