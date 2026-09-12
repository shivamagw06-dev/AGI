"""Real option contracts that have already expired, and what they actually traded at.

The validation loop collects forward: it snapshots a contract, waits five to
thirty minutes, and checks what the model predicted against what happened. That
is the right test, but it means the acceptance gate -- 60 trading days under a
3% error -- is three months away no matter how good the model is, because the
evidence does not exist yet.

Contracts that have already expired are the same test against history. Upstox
keeps six months of them with real candles, so the same comparison can run over
thousands of contracts today instead of accumulating two a day.

Two limits worth stating plainly, because they bound what this can ever do:

  * Six months. Not years. The expiries endpoint returns roughly the last
    twenty-six weekly expiries, so this cannot answer questions about a
    volatility regime older than that.
  * Upstox Plus. The expired-instrument endpoints are a paid tier. probe()
    exists to answer "does this account actually have it" before anyone builds
    a backfill plan on the assumption that it does.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Iterable, Optional

from .upstox_live import API_BASE, UpstoxLiveError, load_access_token

# The chain the collector already watches. Kept as the default so history and
# live evidence describe the same instrument.
NIFTY_KEY = "NSE_INDEX|Nifty 50"

# 1-minute candles for one weekly expiry across a full chain is roughly half a
# million rows; twenty-six expiries of that does not belong on the engine's
# disk. 15 minutes is the coarsest interval that still resolves the 5-30 minute
# horizon the validation loop measures over.
DEFAULT_INTERVAL = "15minute"
INTERVALS = ("1minute", "3minute", "5minute", "15minute", "30minute", "day")


@dataclass(frozen=True)
class ExpiredContract:
    instrument_key: str
    trading_symbol: str
    expiry: str
    strike: float
    option_type: str          # CE | PE
    lot_size: int
    underlying_key: str

    @property
    def is_option(self) -> bool:
        return self.option_type in ("CE", "PE")


def _request(url: str, token: str, timeout: int = 30) -> Any:
    """One GET, returning whatever `data` holds.

    Deliberately not upstox_live._get: that one requires data to be a list, and
    the candle endpoint answers with an object. Sharing it would mean loosening
    a check the live collector benefits from.
    """
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "AGI-Pricing-Engine-V1/1.0",
        },
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if payload.get("status") != "success":
                raise UpstoxLiveError(f"status={payload.get('status')!r}")
            return payload.get("data")
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")[:400]
            if error.code in (401, 403):
                # 403 here usually means the plan, not the token: the live
                # collector keeps working while these endpoints refuse.
                raise UpstoxLiveError(
                    f"HTTP {error.code}: not authorised for expired instruments "
                    f"(Upstox Plus required, or token expired) :: {body}"
                ) from error
            if error.code != 429 and error.code < 500:
                raise UpstoxLiveError(f"HTTP {error.code}: {body}") from error
            if attempt == 2:
                raise UpstoxLiveError(f"HTTP {error.code} after retries: {body}") from error
        except (urllib.error.URLError, TimeoutError) as error:
            if attempt == 2:
                raise UpstoxLiveError(f"request failed after retries: {error}") from error
        time.sleep(2 ** attempt)
    raise UpstoxLiveError("unreachable retry state")


def list_expiries(instrument_key: str = NIFTY_KEY, *,
                  token: Optional[str] = None) -> list[str]:
    """Expiry dates Upstox still holds contracts for, oldest first."""
    token = token or load_access_token()
    query = urllib.parse.urlencode({"instrument_key": instrument_key})
    data = _request(f"{API_BASE}/expired-instruments/expiries?{query}", token)
    return sorted(str(d) for d in (data or []) if str(d).strip())


def list_contracts(expiry: str, instrument_key: str = NIFTY_KEY, *,
                   token: Optional[str] = None) -> list[ExpiredContract]:
    """Every contract that existed for one expiry."""
    token = token or load_access_token()
    query = urllib.parse.urlencode(
        {"instrument_key": instrument_key, "expiry_date": expiry})
    data = _request(f"{API_BASE}/expired-instruments/option/contract?{query}", token)
    out: list[ExpiredContract] = []
    for row in data or []:
        key = str(row.get("instrument_key") or "").strip()
        if not key:
            continue
        try:
            strike = float(row.get("strike_price") or 0.0)
        except (TypeError, ValueError):
            continue
        out.append(ExpiredContract(
            instrument_key=key,
            trading_symbol=str(row.get("trading_symbol") or ""),
            expiry=str(row.get("expiry") or expiry)[:10],
            strike=strike,
            option_type=str(row.get("instrument_type") or "").upper(),
            lot_size=int(row.get("lot_size") or 0),
            underlying_key=str(row.get("underlying_key") or instrument_key),
        ))
    return out


def candles(expired_instrument_key: str, from_date: str, to_date: str, *,
            interval: str = DEFAULT_INTERVAL,
            token: Optional[str] = None) -> list[list[Any]]:
    """OHLC, volume and open interest, oldest first.

    Upstox answers newest-first; reversed here so a caller walking the list
    forward is walking time forward, which is what every consumer wants.
    """
    if interval not in INTERVALS:
        raise ValueError(f"interval must be one of {INTERVALS}")
    token = token or load_access_token()
    path = (f"{API_BASE}/expired-instruments/historical-candle/"
            f"{urllib.parse.quote(expired_instrument_key, safe='')}/"
            f"{interval}/{to_date}/{from_date}")
    data = _request(path, token)
    rows = (data or {}).get("candles") or []
    return list(reversed(rows))


def probe(instrument_key: str = NIFTY_KEY) -> dict[str, Any]:
    """Can this account read expired instruments at all, and how far back.

    Read-only and cheap: three calls at most. Exists because the endpoints are
    a paid tier, and a backfill that discovers this halfway through has already
    wasted an hour.
    """
    result: dict[str, Any] = {"instrument_key": instrument_key}
    try:
        token = load_access_token()
    except Exception as exc:
        return {**result, "ok": False, "stage": "token", "error": str(exc)[:200]}

    try:
        expiries = list_expiries(instrument_key, token=token)
    except UpstoxLiveError as exc:
        return {**result, "ok": False, "stage": "expiries", "error": str(exc)[:300]}
    if not expiries:
        return {**result, "ok": False, "stage": "expiries", "error": "no expiries returned"}

    today = date.today().isoformat()
    past = [e for e in expiries if e < today]
    result.update({
        "expiries_total": len(expiries),
        "expiries_past": len(past),
        "oldest": expiries[0],
        "newest": expiries[-1],
    })
    if not past:
        return {**result, "ok": False, "stage": "expiries",
                "error": "only future expiries returned; no history to read"}

    probe_expiry = past[-1]
    try:
        contracts = list_contracts(probe_expiry, instrument_key, token=token)
    except UpstoxLiveError as exc:
        return {**result, "ok": False, "stage": "contracts",
                "probe_expiry": probe_expiry, "error": str(exc)[:300]}
    options = [c for c in contracts if c.is_option]
    result.update({"probe_expiry": probe_expiry, "contracts": len(contracts),
                   "options": len(options)})
    if not options:
        return {**result, "ok": False, "stage": "contracts",
                "error": "expiry returned no option contracts"}

    sample = sorted(options, key=lambda c: c.strike)[len(options) // 2]
    try:
        rows = candles(sample.instrument_key, probe_expiry, probe_expiry, token=token)
    except UpstoxLiveError as exc:
        return {**result, "ok": False, "stage": "candles",
                "sample": sample.trading_symbol, "error": str(exc)[:300]}
    result.update({
        "sample": sample.trading_symbol,
        "sample_candles": len(rows),
        "sample_first": rows[0] if rows else None,
        "has_open_interest": bool(rows and len(rows[0]) >= 7),
    })
    return {**result, "ok": True, "stage": "complete"}
