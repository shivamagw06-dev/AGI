"""RQ1 Sprint 1 entity lexicon — deterministic resolution for benchmark coverage."""

from __future__ import annotations

import re
from typing import Any

# Canonical company aliases → (display, ticker)
COMPANY_ALIASES: dict[str, tuple[str, str]] = {
    "hdfc bank": ("HDFC Bank", "HDFCBANK"),
    "hdfcbank": ("HDFC Bank", "HDFCBANK"),
    "hdfc": ("HDFC Bank", "HDFCBANK"),  # ambiguous historically; prefer bank for Sprint 1
    "infosys": ("Infosys", "INFY"),
    "infy": ("Infosys", "INFY"),
    "tcs": ("TCS", "TCS"),
    "tata consultancy": ("TCS", "TCS"),
    "tata consultancy services": ("TCS", "TCS"),
    "reliance": ("Reliance Industries", "RELIANCE"),
    "reliance industries": ("Reliance Industries", "RELIANCE"),
    "ril": ("Reliance Industries", "RELIANCE"),
    "icici bank": ("ICICI Bank", "ICICIBANK"),
    "icici": ("ICICI Bank", "ICICIBANK"),
    "icicibank": ("ICICI Bank", "ICICIBANK"),
    "sbi": ("State Bank of India", "SBIN"),
    "state bank": ("State Bank of India", "SBIN"),
    "tata motors": ("Tata Motors", "TATAMOTORS"),
    "tata power": ("Tata Power", "TATAPOWER"),
    "titan": ("Titan", "TITAN"),
    "apple": ("Apple", "AAPL"),
    "microsoft": ("Microsoft", "MSFT"),
    "wipro": ("Wipro", "WIPRO"),
    "hcltech": ("HCL Technologies", "HCLTECH"),
    "hcl": ("HCL Technologies", "HCLTECH"),
}

# Ambiguous stems that must clarify when no disambiguator present
AMBIGUOUS_STEMS: dict[str, list[dict[str, str]]] = {
    "tata": [
        {"entity": "TCS", "ticker": "TCS", "entity_type": "Company"},
        {"entity": "Titan", "ticker": "TITAN", "entity_type": "Company"},
        {"entity": "Tata Motors", "ticker": "TATAMOTORS", "entity_type": "Company"},
        {"entity": "Tata Power", "ticker": "TATAPOWER", "entity_type": "Company"},
    ],
}

SECTOR_ALIASES: dict[str, str] = {
    "banking": "Banking",
    "banks": "Banking",
    "bank": "Banking",
    "it": "Information Technology",
    "information technology": "Information Technology",
    "software": "Information Technology",
    "fmcg": "FMCG",
    "consumer staples": "FMCG",
    "pharma": "Pharmaceuticals",
    "pharmaceuticals": "Pharmaceuticals",
    "auto": "Automobile",
    "automobile": "Automobile",
    "energy": "Energy",
    "oil & gas": "Energy",
    "metals": "Metals",
    "realty": "Real Estate",
    "real estate": "Real Estate",
}

INDEX_ALIASES: dict[str, str] = {
    "nifty it": "Nifty IT",
    "nifty-it": "Nifty IT",
    "cnx it": "Nifty IT",
    "nifty 50": "Nifty 50",
    "nifty50": "Nifty 50",
    "nifty": "Nifty 50",
    "sensex": "Sensex",
    "bse sensex": "Sensex",
    "nasdaq": "Nasdaq Composite",
    "nasdaq composite": "Nasdaq Composite",
    "s&p 500": "S&P 500",
    "spx": "S&P 500",
}

MACRO_ALIASES: dict[str, str] = {
    "rbi": "RBI Policy Rate",
    "rate cut": "Interest Rates",
    "interest rates": "Interest Rates",
    "rates": "Interest Rates",
    "inflation": "Inflation",
    "cpi": "Inflation",
    "oil": "Crude Oil",
    "crude": "Crude Oil",
    "recession": "Recession Risk",
    "us recession": "US Recession Risk",
    "usd/inr": "USD/INR",
    "rupee": "USD/INR",
    "dollar": "USD",
}

COMMODITY_ALIASES: dict[str, str] = {
    "gold": "Gold",
    "silver": "Silver",
    "crude oil": "Crude Oil",
    "brent": "Brent Crude",
}

THEME_ALIASES: dict[str, str] = {
    "ai": "Artificial Intelligence",
    "artificial intelligence": "Artificial Intelligence",
    "ev": "Electric Vehicles",
    "defence": "Defence",
    "defense": "Defence",
}

EDU_CONCEPTS: dict[str, str] = {
    "roic": "ROIC",
    "return on invested capital": "ROIC",
    "ev/ebitda": "EV/EBITDA",
    "evebitda": "EV/EBITDA",
    "dcf": "DCF",
    "discounted cash flow": "DCF",
    "pe": "P/E",
    "p/e": "P/E",
    "pb": "P/B",
}


def _norm(text: str) -> str:
    t = (text or "").lower()
    t = t.replace("&", " and ")
    t = re.sub(r"[^a-z0-9./\s-]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def find_all_alias_hits(text: str, catalog: dict[str, Any]) -> list[tuple[str, Any]]:
    norm = _norm(text)
    hits: list[tuple[str, Any]] = []
    for alias in sorted(catalog.keys(), key=len, reverse=True):
        # word-boundary-ish for short tokens
        if len(alias) <= 3:
            pat = rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])"
            if re.search(pat, norm):
                hits.append((alias, catalog[alias]))
        elif alias in norm:
            hits.append((alias, catalog[alias]))
    # de-dupe by value string
    seen: set[str] = set()
    out: list[tuple[str, Any]] = []
    for alias, val in hits:
        key = str(val)
        if key in seen:
            continue
        seen.add(key)
        out.append((alias, val))
    return out


def resolve_entities(question: str) -> dict[str, Any]:
    """Return best-effort entity resolution for Sprint 1 (no network)."""
    q = question or ""
    norm = _norm(q)

    # Ambiguous stems first (e.g. "Tata" alone)
    for stem, matches in AMBIGUOUS_STEMS.items():
        pat = rf"(?<![a-z0-9]){re.escape(stem)}(?![a-z0-9])"
        if re.search(pat, norm):
            # If a more specific company alias also matches, prefer that
            company_hits = find_all_alias_hits(q, COMPANY_ALIASES)
            specific = [h for h in company_hits if h[0] != stem and stem in h[0] or h[0] in {m["entity"].lower() for m in matches}]
            # e.g. "tata motors" should not clarify
            if any(stem in alias and alias != stem for alias, _ in company_hits):
                break
            if re.fullmatch(rf".*\b{stem}\b.*", norm) and not any(
                alias.startswith(stem + " ") or alias.endswith(" " + stem) for alias, _ in company_hits if alias != stem
            ):
                # only clarify when no longer alias absorbed the stem
                longer = [alias for alias, _ in company_hits if alias != stem and stem in alias]
                if not longer and len(matches) > 1:
                    return {
                        "entity": None,
                        "entity_type": "Unknown",
                        "ticker": None,
                        "entities": [],
                        "requires_clarification": True,
                        "possible_matches": matches,
                        "ambiguity": stem,
                    }

    companies = find_all_alias_hits(q, COMPANY_ALIASES)
    indexes = find_all_alias_hits(q, INDEX_ALIASES)
    sectors = find_all_alias_hits(q, SECTOR_ALIASES)
    macros = find_all_alias_hits(q, MACRO_ALIASES)
    commodities = find_all_alias_hits(q, COMMODITY_ALIASES)
    themes = find_all_alias_hits(q, THEME_ALIASES)
    concepts = find_all_alias_hits(q, EDU_CONCEPTS)

    entities: list[dict[str, Any]] = []
    for alias, (name, ticker) in companies:
        entities.append(
            {"entity": name, "entity_type": "Company", "ticker": ticker, "matched_alias": alias}
        )
    for alias, name in indexes:
        entities.append({"entity": name, "entity_type": "Index", "ticker": None, "matched_alias": alias})
    for alias, name in sectors:
        entities.append({"entity": name, "entity_type": "Sector", "ticker": None, "matched_alias": alias})
    for alias, name in macros:
        entities.append(
            {"entity": name, "entity_type": "Macro Variable", "ticker": None, "matched_alias": alias}
        )
    for alias, name in commodities:
        entities.append(
            {"entity": name, "entity_type": "Commodity", "ticker": None, "matched_alias": alias}
        )
    for alias, name in themes:
        entities.append({"entity": name, "entity_type": "Theme", "ticker": None, "matched_alias": alias})
    for alias, name in concepts:
        entities.append(
            {"entity": name, "entity_type": "Theme", "ticker": None, "matched_alias": alias, "concept": True}
        )

    if "portfolio" in norm or "watchlist" in norm or "my holdings" in norm:
        entities.append(
            {
                "entity": "My Portfolio" if "portfolio" in norm else "Watchlist",
                "entity_type": "Portfolio" if "portfolio" in norm else "Watchlist",
                "ticker": None,
                "matched_alias": "portfolio" if "portfolio" in norm else "watchlist",
            }
        )

    primary = entities[0] if entities else None
    return {
        "entity": (primary or {}).get("entity"),
        "entity_type": (primary or {}).get("entity_type") or "Unknown",
        "ticker": (primary or {}).get("ticker"),
        "entities": entities,
        "requires_clarification": False,
        "possible_matches": [],
        "ambiguity": None,
    }
