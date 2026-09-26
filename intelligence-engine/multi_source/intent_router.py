"""Lightweight intent routing — which external sources Ask should query."""

from __future__ import annotations

import re
from typing import Any


PE_PATTERNS = re.compile(
    r"\b("
    r"private\s*market|private\s*equity|buyout|pe\s*firm|portfolio\s*compan|"
    r"acquisition|acquired|acquire|exit|fundraising|dry\s*powder|"
    r"blackstone|kkr|apollo|carlyle|bain\s*capital|tpg|advent|eqt|vista|"
    r"deal|transaction|gp\b|lbo"
    r")\b",
    re.I,
)

VALUATION_PATTERNS = re.compile(
    r"\b("
    r"valuation|overvalued|undervalued|expensive|cheap|multiple|"
    r"ev/?ebitda|ev/?sales|ev/?revenue|p/?e\b|pe\s*ratio|fcf\s*yield|"
    r"premium|discount|comparables?"
    r")\b",
    re.I,
)

NIFTY_PATTERNS = re.compile(
    r"\b("
    r"nifty|quality\s*score|research\s*score|momentum|agi\s*score|"
    r"highest\s*quality|best\s*capital\s*allocator|ranking|sentiment|"
    r"bullish|bearish|stock\s*research"
    r")\b",
    re.I,
)

STOCK_COMPARE = re.compile(r"\b(compare|vs\.?|versus)\b", re.I)


def route_sources(
    question: str,
    *,
    ticker: str | None = None,
    entities: list[dict[str, Any]] | None = None,
) -> dict[str, bool]:
    q = (question or "").strip()
    pe = bool(PE_PATTERNS.search(q))
    valuation = bool(VALUATION_PATTERNS.search(q))
    nifty = bool(NIFTY_PATTERNS.search(q))

    # Company-centric questions should pull Nifty research when a ticker is known.
    if ticker and (STOCK_COMPARE.search(q) or valuation or re.search(r"\b(score|quality|outlook|view)\b", q, re.I)):
        nifty = True

    # Soft entity tags from ask pipeline
    for ent in entities or []:
        et = str(ent.get("type") or "").lower()
        if et in {"pe_firm", "fund", "transaction", "portfolio_company"}:
            pe = True
        if et == "company" and ticker:
            nifty = nifty or True

    # Always try Nifty when we have a ticker on equity-style questions
    if ticker and not pe:
        nifty = True

    # Valuation monitor for PE/valuation language
    if pe and valuation:
        valuation = True

    return {
        "private_markets": pe,
        "valuation_monitor": valuation or pe,
        "nifty_research": nifty,
        # Always keep KF/KIP/Academy outside this router (handled by existing Ask path)
    }
