"""Fresh Upstox valuation overlay for Hedge Fund Lab screens.

Capital IQ remains the historical record used for medians and percentiles.
This module supplies only the current market-sensitive multiples, loaded in
one warehouse scan rather than one query per company.
"""

from __future__ import annotations

from datetime import datetime
from threading import Lock
from time import monotonic
from typing import Any, Optional


CURRENT_METRICS = frozenset({"pe", "pb", "ev_ebitda"})
FRESH_WITHIN_DAYS = 1
CACHE_SECONDS = 300.0

_cache_lock = Lock()
_cache_loaded_at = 0.0
_cache_reference_date: Optional[str] = None
_cache_by_symbol: dict[str, dict[str, dict[str, Any]]] = {}


def _number(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number <= 0:
        return None
    return number


def _days_between(older: str, newer: str) -> Optional[int]:
    try:
        old = datetime.strptime(str(older)[:10], "%Y-%m-%d").date()
        new = datetime.strptime(str(newer)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None
    return (new - old).days


def _load() -> tuple[Optional[str], dict[str, dict[str, dict[str, Any]]]]:
    from institutional_warehouse import store

    try:
        rows = store.all_rows("valuation_ratios", limit=200_000)
    except Exception:
        return None, {}

    eligible = []
    reference_date: Optional[str] = None
    for row in rows:
        if str(row.get("source") or row.get("provider") or "").lower() != "upstox":
            continue
        symbol = str(row.get("symbol") or "").strip().upper()
        metric = str(row.get("ratio_name") or "").strip().lower()
        as_of = str(row.get("reported_date") or "")[:10]
        value = _number(row.get("company_value"))
        if not symbol or metric not in CURRENT_METRICS or not as_of or value is None:
            continue
        reference_date = max(reference_date or as_of, as_of)
        eligible.append((symbol, metric, as_of, value, row))

    if not reference_date:
        return None, {}

    by_symbol: dict[str, dict[str, dict[str, Any]]] = {}
    for symbol, metric, as_of, value, row in sorted(
        eligible, key=lambda item: item[2], reverse=True
    ):
        if metric in by_symbol.setdefault(symbol, {}):
            continue
        age = _days_between(as_of, reference_date)
        if age is None or age > FRESH_WITHIN_DAYS:
            continue
        by_symbol[symbol][metric] = {
            "value": value,
            "sector_value": _number(row.get("sector_value")),
            "as_of": as_of,
            "freshness": "FRESH",
            "source": "upstox",
            "snapshot_id": row.get("snapshot_id"),
            "dqiv_status": row.get("dqiv_status"),
        }
    return reference_date, by_symbol


def reset_cache() -> None:
    global _cache_loaded_at, _cache_reference_date, _cache_by_symbol
    with _cache_lock:
        _cache_loaded_at = 0.0
        _cache_reference_date = None
        _cache_by_symbol = {}


def current_valuation(symbol: str) -> dict[str, Any]:
    """Return fresh current multiples plus field-level provenance."""
    global _cache_loaded_at, _cache_reference_date, _cache_by_symbol

    now = monotonic()
    if now - _cache_loaded_at >= CACHE_SECONDS:
        with _cache_lock:
            if now - _cache_loaded_at >= CACHE_SECONDS:
                reference, values = _load()
                _cache_reference_date = reference
                _cache_by_symbol = values
                _cache_loaded_at = now

    ticker = str(symbol or "").strip().upper()
    metrics = dict(_cache_by_symbol.get(ticker) or {})
    return {
        "available": bool(metrics),
        "symbol": ticker,
        "source": "upstox" if metrics else None,
        "reference_date": _cache_reference_date,
        "as_of": max((m["as_of"] for m in metrics.values()), default=None),
        "freshness": "FRESH" if metrics else "UNAVAILABLE",
        "metrics": metrics,
    }


def overlay(row: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Overlay current multiples without changing the historical source row."""
    base = dict(row or {})
    live = current_valuation(base.get("symbol"))
    if not live["available"]:
        return base, {
            "source": base.get("source"),
            "as_of": base.get("date"),
            "freshness": "FALLBACK",
            "metrics": {},
        }

    for metric, evidence in live["metrics"].items():
        base[metric] = evidence["value"]
    pe = live["metrics"].get("pe") or {}
    pb = live["metrics"].get("pb") or {}
    if pe.get("sector_value") is not None:
        base["sector_median"] = pe["sector_value"]
    if pb.get("sector_value") is not None:
        base["industry_median"] = pb["sector_value"]

    return base, {
        "source": live["source"],
        "as_of": live["as_of"],
        "reference_date": live["reference_date"],
        "freshness": live["freshness"],
        "metrics": live["metrics"],
        "historical_source": row.get("source"),
        "historical_as_of": row.get("date"),
    }
