"""Latest traded LTP overlay from Live Alpha / Groww snapshots.

Hedge Fund scanners rank on warehouse closes. During the session those closes
lag the tape. Live Alpha already writes `live_market_snapshots` every minute;
this module folds the newest print per instrument and overlays it onto desk
rows so strategy prices match the last observed trade rather than yesterday.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from threading import Lock
from time import monotonic
from typing import Any, Optional
from urllib.parse import quote

CACHE_SECONDS = 20.0
MAX_AGE_MINUTES = 20.0

_cache_lock = Lock()
_cache_loaded_at = 0.0
_cache: dict[str, dict[str, Any]] = {}


def _num(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number and number > 0 else None


def _parse_ts(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        stamp = datetime.fromisoformat(text)
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        return stamp.astimezone(timezone.utc)
    except Exception:
        return None


def reset_cache() -> None:
    global _cache_loaded_at, _cache
    with _cache_lock:
        _cache_loaded_at = 0.0
        _cache = {}


def _fetch_recent_snapshots(*, max_age_minutes: float) -> list[dict[str, Any]]:
    from hedge_fund_lab.live_alpha_bridge import _rest

    since = (datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)).isoformat()
    path = (
        "live_market_snapshots"
        "?select=instrument_key,observed_at,ltp,previous_close"
        f"&observed_at=gte.{quote(since)}"
        "&order=observed_at.desc"
        "&limit=5000"
    )
    rows = _rest(path, timeout_seconds=6.0)
    return rows if isinstance(rows, list) else []


def _symbol_aliases(by_key: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    if not by_key:
        return {}
    try:
        from institutional_warehouse import store
    except Exception:
        return {}
    out = dict(by_key)
    try:
        masters = store.all_rows("company_master", limit=8000) or []
    except Exception:
        return out
    for master in masters:
        key = str(master.get("instrument_key") or "").strip()
        symbol = str(master.get("symbol") or "").strip().upper()
        pack = by_key.get(key)
        if key and symbol and pack is not None:
            out[symbol] = pack
    return out


def _load(*, max_age_minutes: float) -> dict[str, dict[str, Any]]:
    now = datetime.now(timezone.utc)
    folded: dict[str, dict[str, Any]] = {}
    for row in _fetch_recent_snapshots(max_age_minutes=max_age_minutes):
        key = str(row.get("instrument_key") or "").strip()
        ltp = _num(row.get("ltp"))
        observed = _parse_ts(row.get("observed_at"))
        if not key or ltp is None or observed is None:
            continue
        if (now - observed).total_seconds() > max_age_minutes * 60:
            continue
        existing = folded.get(key)
        if existing and _parse_ts(existing.get("observed_at")) and observed <= _parse_ts(existing["observed_at"]):
            continue
        folded[key] = {
            "ltp": ltp,
            "observed_at": observed.isoformat(),
            "previous_close": _num(row.get("previous_close")),
            "source": "live_market_snapshots",
        }
    return _symbol_aliases(folded)


def latest_live_price_map(*, force: bool = False, max_age_minutes: float = MAX_AGE_MINUTES) -> dict[str, dict[str, Any]]:
    global _cache_loaded_at, _cache
    now = monotonic()
    if not force and now - _cache_loaded_at < CACHE_SECONDS:
        return _cache
    with _cache_lock:
        if not force and now - _cache_loaded_at < CACHE_SECONDS:
            return _cache
        try:
            _cache = _load(max_age_minutes=max_age_minutes)
        except Exception:
            _cache = {}
        _cache_loaded_at = now
        return _cache


def lookup_live_price(row: dict[str, Any], latest: dict[str, dict[str, Any]] | None = None) -> Optional[dict[str, Any]]:
    prices = latest if latest is not None else latest_live_price_map()
    if not prices:
        return None
    key = str(row.get("instrument_key") or "").strip()
    symbol = str(row.get("ticker") or row.get("symbol") or "").strip().upper()
    return prices.get(key) or prices.get(symbol)


def apply_latest_live_price(
    row: dict[str, Any],
    latest: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    pack = lookup_live_price(row, latest)
    if not pack:
        return row
    ltp = pack["ltp"]
    out = dict(row)
    prior_price = _num(out.get("price") or out.get("cmp"))
    prior_yield = _num(out.get("dividend_yield"))
    forward_eps = _num(out.get("forward_eps") or (out.get("factors") or {}).get("forward_eps"))
    out["price"] = ltp
    out["cmp"] = ltp
    out["live_price"] = ltp
    out["price_source"] = pack.get("source")
    out["price_as_of"] = pack.get("observed_at")
    context = dict(out.get("data_context") or {})
    context["price_source"] = pack.get("source")
    context["price_as_of"] = pack.get("observed_at")
    context["price_freshness"] = "LIVE"
    out["data_context"] = context
    consensus = dict(out.get("consensus") or {})
    target = _num(consensus.get("target_price")) or _num(out.get("target_price"))
    if target is not None:
        consensus["target_price"] = target
        consensus["upside"] = round((target / ltp - 1.0) * 100.0, 2)
        out["consensus"] = consensus
        out["consensus_upside"] = consensus["upside"]
        out["target_price"] = target
    if prior_price and prior_yield is not None:
        dps = (prior_yield / 100.0) * prior_price
        out["dividend_yield"] = round((dps / ltp) * 100.0, 2)
        if _num(out.get("value")) == prior_yield:
            out["value"] = out["dividend_yield"]
    if forward_eps:
        out["forward_pe"] = round(ltp / forward_eps, 2)
    market = out.get("market")
    if isinstance(market, dict):
        market = dict(market)
        market["price"] = ltp
        out["market"] = market
    _recompute_return_1y(out, ltp)
    return out


def _recompute_return_1y(row: dict[str, Any], last_price: float) -> None:
    """Keep 1Y on the same last price the page is showing.

    Overlaying LTP without touching the year left SUNTECK at +23% against a
    live print of 314, while the stock was down 20% over the year.
    """
    context = dict(row.get("data_context") or {})
    base = _num(context.get("return_1y_base_close")) or _num(row.get("return_1y_base_close"))
    if not (base and last_price and base > 0):
        return
    try:
        from hedge_fund_lab.scanner import RETURN_CEILING_PCT, RETURN_FLOOR_PCT
    except Exception:
        RETURN_FLOOR_PCT, RETURN_CEILING_PCT = -60.0, 200.0
    value = round((last_price / base - 1.0) * 100.0, 2)
    consensus = dict(row.get("consensus") or {})
    if value < RETURN_FLOOR_PCT or value > RETURN_CEILING_PCT:
        consensus["return_1y"] = None
        row["return_1y"] = None
        row["consensus"] = consensus
        return
    consensus["return_1y"] = value
    row["consensus"] = consensus
    row["return_1y"] = value


def overlay_live_prices_on_payload(payload: Any, latest: dict[str, dict[str, Any]] | None = None) -> Any:
    """Walk a terminal/scan payload and stamp the newest LTP onto name rows.

    Hedge Fund GET serves a stored snapshot. Overlaying at read time keeps the
    research ranks stable while the displayed price tracks the tape.
    """
    prices = latest if latest is not None else latest_live_price_map()
    if not prices:
        return payload
    return _overlay_walk(payload, prices)


def _overlay_walk(obj: Any, prices: dict[str, dict[str, Any]]) -> Any:
    if isinstance(obj, list):
        return [_overlay_walk(item, prices) for item in obj]
    if not isinstance(obj, dict):
        return obj
    walked = {key: _overlay_walk(value, prices) for key, value in obj.items()}
    if walked.get("ticker") or walked.get("instrument_key") or walked.get("symbol"):
        return apply_latest_live_price(walked, prices)
    return walked
