"""Step 2 — Financial entity resolution."""

from __future__ import annotations

import re

from app.irp.models import ResolvedEntityPack
from app.irp.universes import COMPANY_ALIASES, SECTOR_UNIVERSES
from app.kip.extractors import looks_like_equity_ticker

_TICKER_RE = re.compile(r"\b([A-Z]{2,12})(?:\.(?:NS|BO))?\b")


def resolve_entities(question: str, *, ticker: str | None = None) -> ResolvedEntityPack:
    q = (question or "").strip()
    ql = q.lower()
    pack = ResolvedEntityPack()

    # Sector universe first (e.g. Indian IT services)
    for key, uni in SECTOR_UNIVERSES.items():
        if any(a in ql for a in uni["aliases"]):
            pack.sector_key = key
            pack.sector_label = uni["label"]
            pack.sector = uni["sector"]
            pack.companies = list(uni["companies"])
            pack.tickers = [c["ticker"] for c in uni["companies"]]
            pack.themes = list(uni["themes"])
            pack.currencies = list(uni["currencies"])
            pack.countries = list(uni["countries"])
            pack.macro_drivers = list(uni["macro_drivers"])
            pack.reject_topics = list(uni["reject_topics"])
            break

    # Explicit / inferred company tickers
    found: list[str] = []
    if ticker:
        t = str(ticker).upper().replace(".NS", "").replace(".BO", "")
        if looks_like_equity_ticker(t):
            found.append(t)
    for m in _TICKER_RE.finditer(q.upper()):
        tok = m.group(1).upper()
        if looks_like_equity_ticker(tok):
            found.append(tok)
    for alias, tkr in COMPANY_ALIASES.items():
        if alias in ql:
            found.append(tkr)

    # Deduplicate preserving order
    seen: set[str] = set()
    ordered: list[str] = []
    for t in found:
        if t not in seen:
            seen.add(t)
            ordered.append(t)

    if ordered:
        pack.primary_ticker = ordered[0]
        for t in ordered:
            if t not in pack.tickers:
                pack.tickers.append(t)
                name = next((c["name"] for c in pack.companies if c.get("ticker") == t), t)
                if not any(c.get("ticker") == t for c in pack.companies):
                    pack.companies.append({"ticker": t, "name": name})

    # Theme keywords
    theme_map = {
        "ai": "ai_adoption",
        "generative ai": "ai_adoption",
        "cloud": "cloud",
        "digital": "digital_transformation",
        "outsourcing": "global_outsourcing",
    }
    for key, theme in theme_map.items():
        if key in ql and theme not in pack.themes:
            pack.themes.append(theme)

    if "india" in ql and "India" not in pack.countries:
        pack.countries.append("India")
    if any(x in ql for x in ("us ", "u.s", "united states", "america")) and "United States" not in pack.countries:
        pack.countries.append("United States")

    return pack
