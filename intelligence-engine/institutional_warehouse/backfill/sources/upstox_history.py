"""True daily OHLCV from Upstox, which is what the warehouse has been missing.

The Yahoo backfill reported success for all 2,710 companies and wrote roughly
245 rows each. That looked like coverage and was not: Yahoo silently downsamples
`range=max&interval=1d` to monthly bars on long ranges, so daily_market_history
became a monthly series from 1995 with a daily tail bolted on from the NSE
bhavcopy in September 2025. Median spacing between observations was 28 to 30
days, which makes every metric that annualises by 252 wrong by about sqrt(20).

Upstox v3 historical candles fix all of that at once:

* genuinely daily, back to 2000-01-03, verified at a median gap of 1 day
* already corporate-action adjusted - RELIANCE runs through its September 2017
  1:1 bonus at about 389 with no break - so none of the ratio guessing in
  price_adjustment is needed for this series
* public data, no access token, unlike the rest of the Upstox surface

The one constraint is a maximum span of roughly ten years per request, so
history is pulled in windows and stitched. Requests are ordered newest first so
a partial run still leaves the most useful history in place.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime
from typing import Any, Callable, Iterable, Optional

SOURCE = "upstox_v3_historical"
BASE = "https://api.upstox.com/v3/historical-candle"
# Upstox rejects spans much beyond a decade with UDAPI1148 "Invalid date range".
MAX_WINDOW_YEARS = 9
EARLIEST = date(2000, 1, 1)
# Upstox answers 403 to the default urllib agent even on the public candle
# endpoint, so it has to look like an ordinary client.
USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def to_number(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if out == out and out not in (float("inf"), float("-inf")) else None


def instrument_key(company: dict[str, Any]) -> Optional[str]:
    """`NSE_EQ|<isin>`, taken from company_master or derived from the ISIN."""
    key = str(company.get("instrument_key") or "").strip()
    if "|" in key:
        return key
    isin = str(company.get("isin") or "").strip().upper()
    return f"NSE_EQ|{isin}" if len(isin) == 12 and isin[:2].isalpha() else None


def windows(start: date, end: date, span_years: int = MAX_WINDOW_YEARS) -> list[tuple[date, date]]:
    """Newest-first request windows, so a partial run keeps recent history."""
    out: list[tuple[date, date]] = []
    upper = end
    while upper > start:
        try:
            lower = upper.replace(year=upper.year - span_years)
        except ValueError:  # 29 February
            lower = upper.replace(year=upper.year - span_years, day=28)
        if lower < start:
            lower = start
        out.append((lower, upper))
        upper = lower
    return out


def candle_url(key: str, from_: date, to: date, *, unit: str = "days", interval: int = 1) -> str:
    return (f"{BASE}/{urllib.parse.quote(key, safe='')}/{unit}/{interval}"
            f"/{to.isoformat()}/{from_.isoformat()}")


def parse_candles(payload: dict[str, Any], *, symbol: str) -> list[dict[str, Any]]:
    """Upstox candle arrays into warehouse rows. Pure: no network, no clock.

    A candle is [timestamp, open, high, low, close, volume, open_interest].
    """
    candles = ((payload or {}).get("data") or {}).get("candles") or []
    rows: list[dict[str, Any]] = []
    for candle in candles:
        if not isinstance(candle, (list, tuple)) or len(candle) < 6:
            continue
        close = to_number(candle[4])
        stamp = str(candle[0] or "")[:10]
        if close is None or close <= 0 or len(stamp) != 10:
            continue
        try:
            date.fromisoformat(stamp)
        except ValueError:
            continue
        rows.append({
            "symbol": symbol,
            "date": stamp,
            "open": to_number(candle[1]),
            "high": to_number(candle[2]),
            "low": to_number(candle[3]),
            "close": close,
            # Upstox candles are already adjusted, so the adjusted column is the
            # same series rather than a copy of an unadjusted close. The warehouse
            # column previously equalled close while reflecting no action at all.
            "adjusted_close": close,
            "volume": to_number(candle[5]),
            "source": SOURCE,
        })
    return rows


def _http_get(url: str, *, timeout: int = 45) -> dict[str, Any]:
    request = urllib.request.Request(
        url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_history(
    symbol: str,
    key: str,
    *,
    start: date = EARLIEST,
    end: Optional[date] = None,
    getter: Optional[Callable[[str], dict[str, Any]]] = None,
    pause_seconds: float = 0.0,
) -> dict[str, Any]:
    """Stitch every window into one daily series for a single company."""
    ticker = str(symbol).upper()
    finish = end or date.today()
    get = getter or _http_get
    by_date: dict[str, dict[str, Any]] = {}
    errors: list[str] = []

    for lower, upper in windows(start, finish):
        try:
            payload = get(candle_url(key, lower, upper))
        except urllib.error.HTTPError as exc:
            # A window before listing returns an error rather than an empty set;
            # that is not a failure of the run, it is the start of the history.
            errors.append(f"{lower}..{upper}: HTTP {exc.code}")
            continue
        except Exception as exc:
            errors.append(f"{lower}..{upper}: {str(exc)[:80]}")
            continue
        for row in parse_candles(payload, symbol=ticker):
            by_date[row["date"]] = row
        if pause_seconds:
            import time

            time.sleep(pause_seconds)

    rows = [by_date[day] for day in sorted(by_date)]
    return {
        "ok": bool(rows),
        "symbol": ticker,
        "instrument_key": key,
        "prices": rows,
        "first": rows[0]["date"] if rows else None,
        "last": rows[-1]["date"] if rows else None,
        "errors": errors,
        "error": None if rows else (errors[0] if errors else "no_candles_returned"),
    }


def daily_share(rows: Iterable[dict[str, Any]]) -> float:
    """Share of gaps that are 1-4 days. The check Yahoo's output would fail."""
    days = sorted({date.fromisoformat(r["date"]) for r in rows if r.get("date")})
    gaps = [(b - a).days for a, b in zip(days, days[1:])]
    if not gaps:
        return 0.0
    return sum(1 for gap in gaps if 1 <= gap <= 4) / len(gaps)
