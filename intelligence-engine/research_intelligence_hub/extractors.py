"""Deterministic entity / topic extraction for research notes — no live feeds."""

from __future__ import annotations

import re
from typing import Any

KNOWN_TICKERS = {
    "ICICIBANK": {"name": "ICICI Bank", "sector": "Banking"},
    "HDFCBANK": {"name": "HDFC Bank", "sector": "Banking"},
    "SBIN": {"name": "State Bank of India", "sector": "Banking"},
    "AXISBANK": {"name": "Axis Bank", "sector": "Banking"},
    "KOTAKBANK": {"name": "Kotak Mahindra Bank", "sector": "Banking"},
    "RELIANCE": {"name": "Reliance Industries", "sector": "Energy"},
    "TCS": {"name": "Tata Consultancy Services", "sector": "IT Services"},
    "INFY": {"name": "Infosys", "sector": "IT Services"},
    "WIPRO": {"name": "Wipro", "sector": "IT Services"},
    "HCLTECH": {"name": "HCL Technologies", "sector": "IT Services"},
    "LT": {"name": "Larsen & Toubro", "sector": "Capital Goods"},
    "SIEMENS": {"name": "Siemens", "sector": "Capital Goods"},
    "MARUTI": {"name": "Maruti Suzuki", "sector": "Auto"},
    "TATAMOTORS": {"name": "Tata Motors", "sector": "Auto"},
    "ITC": {"name": "ITC", "sector": "FMCG"},
    "HINDUNILVR": {"name": "Hindustan Unilever", "sector": "FMCG"},
    "SUNPHARMA": {"name": "Sun Pharma", "sector": "Pharma"},
    "DRREDDY": {"name": "Dr Reddy's", "sector": "Pharma"},
    "BHARTIARTL": {"name": "Bharti Airtel", "sector": "Telecom"},
}

NAME_TO_TICKER = {
    "icici bank": "ICICIBANK",
    "hdfc bank": "HDFCBANK",
    "state bank": "SBIN",
    "sbi": "SBIN",
    "infosys": "INFY",
    "reliance": "RELIANCE",
    "l&t": "LT",
    "larsen": "LT",
    "maruti": "MARUTI",
    "tata motors": "TATAMOTORS",
    "hindustan unilever": "HINDUNILVR",
    "hul": "HINDUNILVR",
}

SECTOR_LEXICON = {
    "banking": "Banking",
    "banks": "Banking",
    "financials": "Banking",
    "it services": "IT Services",
    "information technology": "IT Services",
    "software": "IT Services",
    "fmcg": "FMCG",
    "consumer staples": "FMCG",
    "auto": "Auto",
    "automobile": "Auto",
    "automobiles": "Auto",
    "capital goods": "Capital Goods",
    "industrials": "Capital Goods",
    "defence": "Defence",
    "defense": "Defence",
    "pharma": "Pharma",
    "pharmaceuticals": "Pharma",
    "energy": "Energy",
    "oil": "Energy",
    "telecom": "Telecom",
}

MACRO_LEXICON = {
    "inflation": "Inflation",
    "cpi": "Inflation",
    "rbi": "RBI",
    "repo": "Interest Rates",
    "interest rate": "Interest Rates",
    "rate cut": "Interest Rates",
    "rate hike": "Interest Rates",
    "gdp": "GDP",
    "growth": "GDP",
    "currency": "Currency",
    "rupee": "Currency",
    "usdinr": "Currency",
    "dollar": "Currency",
    "oil": "Commodities",
    "crude": "Commodities",
    "commodity": "Commodities",
    "gold": "Commodities",
    "fiscal": "Fiscal Policy",
    "budget": "Fiscal Policy",
    "capex": "Fiscal Policy",
    "liquidity": "Liquidity",
    "fii": "Institutional Flows",
    "dii": "Institutional Flows",
}

MARKET_LEXICON = {
    "nifty": "India Equity",
    "sensex": "India Equity",
    "india market": "India Equity",
    "bull market": "India Equity",
    "bear market": "India Equity",
    "correction": "India Equity",
    "breadth": "Market Breadth",
    "volatility": "Volatility",
    "vix": "Volatility",
    "liquidity": "Liquidity",
}

GLOBAL_LEXICON = {
    "us market": "US Markets",
    "s&p": "US Markets",
    "nasdaq": "US Markets",
    "fed": "US Markets",
    "europe": "Europe",
    "ecb": "Europe",
    "china": "China",
    "japan": "Japan",
    "boj": "Japan",
    "emerging markets": "Emerging Markets",
    "em": "Emerging Markets",
    "bond": "Bond Markets",
    "treasury": "Bond Markets",
    "yield": "Bond Markets",
}

HISTORY_LEXICON = {
    "covid": "COVID Recovery",
    "pandemic": "COVID Recovery",
    "2008": "2008 Financial Crisis",
    "gfc": "2008 Financial Crisis",
    "taper": "2013 Taper Tantrum",
    "2013": "2013 Taper Tantrum",
    "demonetisation": "Demonetisation",
    "demonetization": "Demonetisation",
    "il&fs": "Banking Stress",
    "npa": "Banking Stress",
    "rate cycle": "Previous RBI Cycles",
}

IPO_LEXICON = {
    "ipo": "IPO Activity",
    "listing": "Listed IPOs",
    "offer for sale": "Upcoming IPOs",
    "draft red herring": "Upcoming IPOs",
    "drhp": "Upcoming IPOs",
}

_TICKER_RE = re.compile(r"\b([A-Z]{2,10})(?:\.(?:NS|BO))?\b")


def _blob(headline: str, body: str) -> str:
    return f"{headline or ''}\n{body or ''}".lower()


def extract_companies(headline: str, body: str, *, hinted: list[str] | None = None) -> list[dict[str, Any]]:
    text = f"{headline or ''} {body or ''}"
    found: dict[str, dict[str, Any]] = {}
    for t in hinted or []:
        key = str(t).upper()
        meta = KNOWN_TICKERS.get(key) or {"name": key, "sector": None}
        found[key] = {
            "id": key,
            "label": meta["name"],
            "kind": "company",
            "role": "mentioned",
            "href": f"/research/stocks/{key}",
            "gateway": "Company_Intelligence",
            "meta": {"sector": meta.get("sector")},
        }
    for m in _TICKER_RE.findall(text):
        if m in KNOWN_TICKERS:
            meta = KNOWN_TICKERS[m]
            found[m] = {
                "id": m,
                "label": meta["name"],
                "kind": "company",
                "role": "mentioned",
                "href": f"/research/stocks/{m}",
                "gateway": "Company_Intelligence",
                "meta": {"sector": meta.get("sector")},
            }
    low = text.lower()
    for name, ticker in NAME_TO_TICKER.items():
        if name in low and ticker not in found:
            meta = KNOWN_TICKERS[ticker]
            found[ticker] = {
                "id": ticker,
                "label": meta["name"],
                "kind": "company",
                "role": "mentioned",
                "href": f"/research/stocks/{ticker}",
                "gateway": "Company_Intelligence",
                "meta": {"sector": meta.get("sector")},
            }
    # Related peers for primary sector
    sectors = { (v.get("meta") or {}).get("sector") for v in found.values() }
    for ticker, meta in KNOWN_TICKERS.items():
        if meta.get("sector") in sectors and ticker not in found and len(found) < 12:
            found[ticker] = {
                "id": ticker,
                "label": meta["name"],
                "kind": "company",
                "role": "related",
                "href": f"/research/stocks/{ticker}",
                "gateway": "Company_Intelligence",
                "meta": {"sector": meta.get("sector")},
            }
    return list(found.values())


def _match_lexicon(blob: str, lexicon: dict[str, str], *, kind: str, href_prefix: str, gateway: str) -> list[dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for needle, label in lexicon.items():
        if needle in blob:
            key = label.lower().replace(" ", "_")
            out[key] = {
                "id": key,
                "label": label,
                "kind": kind,
                "role": "primary" if needle in blob[:200] else "secondary",
                "href": f"{href_prefix}/{key}",
                "gateway": gateway,
                "meta": {"matched_term": needle},
            }
    return list(out.values())


def extract_sectors(headline: str, body: str, companies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blob = _blob(headline, body)
    rows = _match_lexicon(
        blob, SECTOR_LEXICON, kind="sector", href_prefix="/sectors", gateway="Sector_Intelligence"
    )
    seen = {r["label"] for r in rows}
    for c in companies:
        sec = (c.get("meta") or {}).get("sector")
        if sec and sec not in seen:
            key = sec.lower().replace(" ", "_")
            rows.append(
                {
                    "id": key,
                    "label": sec,
                    "kind": "sector",
                    "role": "primary" if c.get("role") == "mentioned" else "beneficiary",
                    "href": f"/sectors/{key}",
                    "gateway": "Sector_Intelligence",
                    "meta": {},
                }
            )
            seen.add(sec)
    if not rows:
        rows.append(
            {
                "id": "market_wide",
                "label": "Market-wide",
                "kind": "sector",
                "role": "affected",
                "href": "/sectors/market_wide",
                "gateway": "Sector_Intelligence",
                "meta": {},
            }
        )
    return rows


def extract_markets(headline: str, body: str) -> list[dict[str, Any]]:
    blob = _blob(headline, body)
    rows = _match_lexicon(
        blob, MARKET_LEXICON, kind="market", href_prefix="/markets", gateway="Market_Intelligence"
    )
    if not rows:
        rows.append(
            {
                "id": "india_equity",
                "label": "India Equity",
                "kind": "market",
                "role": "primary",
                "href": "/markets/india_equity",
                "gateway": "Market_Intelligence",
                "meta": {"regime_hint": "watch"},
            }
        )
    return rows


def extract_macro(headline: str, body: str) -> list[dict[str, Any]]:
    return _match_lexicon(
        _blob(headline, body),
        MACRO_LEXICON,
        kind="macro",
        href_prefix="/macro",
        gateway="Macro_Intelligence",
    )


def extract_global(headline: str, body: str) -> list[dict[str, Any]]:
    return _match_lexicon(
        _blob(headline, body),
        GLOBAL_LEXICON,
        kind="global",
        href_prefix="/global",
        gateway="Global_Intelligence",
    )


def extract_ipo(headline: str, body: str) -> list[dict[str, Any]]:
    return _match_lexicon(
        _blob(headline, body),
        IPO_LEXICON,
        kind="ipo",
        href_prefix="/ipo",
        gateway="IPO_Intelligence",
    )


def extract_historical_context(headline: str, body: str) -> list[dict[str, Any]]:
    rows = _match_lexicon(
        _blob(headline, body),
        HISTORY_LEXICON,
        kind="historical_event",
        href_prefix="/history",
        gateway="Historical_Intelligence",
    )
    if not rows:
        rows = [
            {
                "id": "previous_rbi_cycles",
                "label": "Previous RBI Cycles",
                "kind": "historical_event",
                "role": "context",
                "href": "/history/previous_rbi_cycles",
                "gateway": "Historical_Intelligence",
                "meta": {},
            },
            {
                "id": "2013_taper_tantrum",
                "label": "2013 Taper Tantrum",
                "kind": "historical_event",
                "role": "context",
                "href": "/history/2013_taper_tantrum",
                "gateway": "Historical_Intelligence",
                "meta": {},
            },
        ]
    return rows


def infer_session(headline: str, body: str, *, session: str | None = None) -> str | None:
    if session:
        return session
    blob = _blob(headline, body)
    if "pre-market" in blob or "pre market" in blob:
        return "Pre Market"
    if "post-market" in blob or "after market" in blob:
        return "Post Market"
    if "global" in blob or "overnight" in blob:
        return "Global"
    if "morning" in blob:
        return "Morning"
    if "afternoon" in blob:
        return "Afternoon"
    return "Morning"


def build_executive_summary(headline: str, body: str, companies: list[dict[str, Any]], sectors: list[dict[str, Any]]) -> dict[str, Any]:
    company_labels = [c["label"] for c in companies if c.get("role") == "mentioned"][:4]
    sector_labels = [s["label"] for s in sectors][:3]
    focus = ", ".join(company_labels) if company_labels else (", ".join(sector_labels) or "India markets")
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", body or "") if s.strip()]
    summary = sentences[:3] if sentences else [
        f"{headline} — institutional briefing centred on {focus}.",
        "Evidence links are assembled dynamically from AGI intelligence platforms.",
        "Outlook is multi-path (Bull / Base / Bear), never a single predicted outcome.",
    ]
    thesis = (
        f"Institutional thesis around {focus}: track transmission through markets, "
        f"macro and sector leadership with evidence-backed scenario paths."
    )
    conclusions = [
        f"Primary focus: {focus}",
        "Navigate via linked companies, sectors, macro topics and market regime.",
        "Validate with historical analogues, relationships and forecast probabilities.",
    ]
    why = [
        f"This note is an Intelligence Hub for {focus}.",
        "Related AGI platforms refresh dynamically — the note stores references, not stale copies.",
        "Users can traverse the full institutional graph without a new search.",
    ]
    return {
        "executive_summary": summary[:5],
        "investment_thesis": thesis,
        "key_conclusions": conclusions,
        "why_it_matters": why,
    }
