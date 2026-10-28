"""Which Indian equities can actually be held short for a month.

This is the constraint that decides whether a long-short result is real. In
India a cash-segment short must be squared off the same session, so a position
held across a monthly rebalance can only exist through single-stock futures or
the securities lending window. Futures are the practical route, and the NSE
instrument master says exactly which names have them: 214 underlyings, against
1,024 companies carrying a consensus-revision signal.

So a decile spread computed over the whole signal universe is not a portfolio
anyone could have run. Roughly four names in five in the bottom decile cannot
be shorted at all, and the ones that can are the largest and most heavily
arbitraged in the market - precisely where a mispricing is least likely to
survive.

Nothing here models the basis. An Indian single-stock future usually trades at
a premium that decays into expiry, so a short earns carry while forgoing the
cash return; the two partly offset and the residual varies by name and month.
It is left out and declared rather than guessed at.
"""

from __future__ import annotations

import gzip
import json
import time
import urllib.request
from typing import Any, Callable, Iterable, Optional

INSTRUMENTS_URL = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"
USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36")
# The master is a 2MB gzip and changes on expiry, not intraday.
CACHE_TTL_SECONDS = 6 * 60 * 60
# Securities-lending fee on a liquid F&O name, annualised. Hard-to-borrow names
# cost multiples of this, so it is a floor rather than an estimate.
DEFAULT_BORROW_BPS_PA = 100.0

_CACHE: dict[str, Any] = {"at": 0.0, "symbols": None}


def _download() -> list[dict[str, Any]]:
    request = urllib.request.Request(INSTRUMENTS_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(gzip.decompress(response.read()).decode("utf-8"))


def parse_shortable(rows: Iterable[dict[str, Any]]) -> set[str]:
    """Underlying symbols that have a single-stock future.

    Index futures are excluded: they carry no underlying equity symbol, and a
    strategy ranking individual companies cannot short an index as a substitute
    for the names it actually wants.
    """
    out: set[str] = set()
    for row in rows or []:
        if row.get("segment") != "NSE_FO" or row.get("instrument_type") != "FUT":
            continue
        symbol = str(row.get("underlying_symbol") or row.get("asset_symbol") or "").strip().upper()
        if symbol:
            out.add(symbol)
    return out


def shortable_symbols(
    *,
    getter: Optional[Callable[[], list[dict[str, Any]]]] = None,
    ttl_seconds: float = CACHE_TTL_SECONDS,
) -> set[str]:
    """Cached shortable universe. Empty set when the master is unreachable.

    An empty set is a refusal, not a permissive default: callers must treat
    "unknown" as "cannot short", or an outage would silently restore the
    unconstrained result this module exists to prevent.
    """
    now = time.time()
    cached = _CACHE.get("symbols")
    if cached is not None and (now - float(_CACHE.get("at") or 0.0)) < ttl_seconds:
        return cached
    try:
        symbols = parse_shortable((getter or _download)())
    except Exception:
        symbols = set()
    if symbols:
        _CACHE["at"] = time.time()
        _CACHE["symbols"] = symbols
    return symbols


def reset_cache() -> None:
    _CACHE["at"] = 0.0
    _CACHE["symbols"] = None


def monthly_borrow_cost(borrow_bps_pa: float = DEFAULT_BORROW_BPS_PA) -> float:
    """One month of borrow, as a decimal drag on the short leg."""
    return (max(0.0, borrow_bps_pa) / 10_000.0) / 12.0
