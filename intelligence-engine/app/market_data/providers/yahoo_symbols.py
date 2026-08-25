"""Yahoo symbol resolution — NSE/BSE/US aliases → Yahoo tickers."""

from __future__ import annotations

import re

# Explicit NSE mappings for AGI tracked universe + common aliases
NSE_YAHOO: dict[str, str] = {
    "HDFCBANK": "HDFCBANK.NS",
    "ICICIBANK": "ICICIBANK.NS",
    "SBIN": "SBIN.NS",
    "AXISBANK": "AXISBANK.NS",
    "KOTAKBANK": "KOTAKBANK.NS",
    "INFY": "INFY.NS",
    "TCS": "TCS.NS",
    "WIPRO": "WIPRO.NS",
    "HCLTECH": "HCLTECH.NS",
    "TECHM": "TECHM.NS",
    "RELIANCE": "RELIANCE.NS",
    "ULTRACEMCO": "ULTRACEMCO.NS",
    "ASIANPAINT": "ASIANPAINT.NS",
    "TATASTEEL": "TATASTEEL.NS",
    "SUNPHARMA": "SUNPHARMA.NS",
    "POWERGRID": "POWERGRID.NS",
    "ITC": "ITC.NS",
    "HINDUNILVR": "HINDUNILVR.NS",
    "BHARTIARTL": "BHARTIARTL.NS",
    "LT": "LT.NS",
    "M&M": "M&M.NS",
    "BAJFINANCE": "BAJFINANCE.NS",
    "NESTLEIND": "NESTLEIND.NS",
    "MARUTI": "MARUTI.NS",
    "TITAN": "TITAN.NS",
    "NTPC": "NTPC.NS",
    "ONGC": "ONGC.NS",
}

# US / global listings that must NEVER get a .NS suffix (META.NS 404 loops hang Ask).
US_YAHOO: dict[str, str] = {
    "META": "META",
    "FB": "META",
    "AAPL": "AAPL",
    "MSFT": "MSFT",
    "GOOGL": "GOOGL",
    "GOOG": "GOOG",
    "AMZN": "AMZN",
    "NVDA": "NVDA",
    "TSLA": "TSLA",
    "NFLX": "NFLX",
    "AMD": "AMD",
    "INTC": "INTC",
    "CRM": "CRM",
    "ORCL": "ORCL",
    "ADBE": "ADBE",
    "AVGO": "AVGO",
    "COST": "COST",
    "PEP": "PEP",
    "KO": "KO",
    "JPM": "JPM",
    "V": "V",
    "MA": "MA",
    "BRK.B": "BRK-B",
    "BRK-B": "BRK-B",
}

QUERY_ALIASES: dict[str, str] = {
    "hdfc bank": "HDFCBANK.NS",
    "hdfc": "HDFCBANK.NS",
    "infosys": "INFY.NS",
    "reliance": "RELIANCE.NS",
    "reliance industries": "RELIANCE.NS",
    "ultratech": "ULTRACEMCO.NS",
    "ultratech cement": "ULTRACEMCO.NS",
    "asian paints": "ASIANPAINT.NS",
    "tata steel": "TATASTEEL.NS",
    "sun pharma": "SUNPHARMA.NS",
    "power grid": "POWERGRID.NS",
    "tcs": "TCS.NS",
    "meta": "META",
    "meta platforms": "META",
    "facebook": "META",
    "apple": "AAPL",
    "microsoft": "MSFT",
    "amazon": "AMZN",
    "nvidia": "NVDA",
    "google": "GOOGL",
    "alphabet": "GOOGL",
}


def to_yahoo_symbol(symbol: str | None, *, exchange: str = "NSE") -> str:
    """Map AGI ticker / query fragment to Yahoo symbol.

    Request-scoped memoisation prevents META→META.NS re-resolution storms.
    """
    raw = (symbol or "").strip()
    if not raw:
        return ""

    # Callers that own exchange identity can explicitly mark an unqualified US
    # ticker. This prevents a legitimate but unknown US symbol being silently
    # rewritten as an NSE listing by the India-first default below.
    explicit_us = raw.upper().startswith("US:")
    if explicit_us:
        raw = raw[3:].strip()
        exchange = "US"
        if not raw:
            return ""

    cache_key = f"ysym:{raw.upper()}|{exchange.upper()}"
    try:
        from app.market_data.providers.yahoo_request_cache import cached_get, cached_set

        hit = cached_get(cache_key)
        if isinstance(hit, str) and hit:
            return hit
    except Exception:
        cached_get = cached_set = None  # type: ignore[assignment]

    # Already a Yahoo-qualified symbol
    if raw.endswith((".NS", ".BO")) or any(x in raw for x in ("=", "^")):
        result = raw
    else:
        upper = raw.upper().replace("BRK.B", "BRK-B")
        if upper in US_YAHOO:
            result = US_YAHOO[upper]
        elif upper in NSE_YAHOO:
            result = NSE_YAHOO[upper]
        elif raw.lower() in QUERY_ALIASES:
            result = QUERY_ALIASES[raw.lower()]
        else:
            compact = re.sub(r"\s+", "", upper)
            if compact in US_YAHOO:
                result = US_YAHOO[compact]
            elif compact in NSE_YAHOO:
                result = NSE_YAHOO[compact]
            elif exchange.upper() == "BSE":
                result = f"{upper}.BO"
            elif exchange.upper() in {"US", "NYSE", "NASDAQ"}:
                result = upper
            else:
                # Default India NSE for unknown short symbols
                result = f"{upper}.NS"

    if cached_set is not None:
        try:
            cached_set(cache_key, result)
        except Exception:
            pass
    return result


def from_yahoo_symbol(yahoo_symbol: str | None) -> str:
    """Strip exchange suffix for AGI canonical ticker."""
    s = (yahoo_symbol or "").strip().upper()
    if s.endswith(".NS") or s.endswith(".BO"):
        return s[:-3]
    if s == "FB":
        return "META"
    return s
