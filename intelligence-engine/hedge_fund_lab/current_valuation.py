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


CURRENT_METRICS = frozenset({"pe", "pb", "ev_ebitda", "roe", "roa", "roce"})
FRESH_WITHIN_DAYS = 1
CACHE_SECONDS = 300.0

_cache_lock = Lock()
_cache_loaded_at = 0.0
_cache_reference_date: Optional[str] = None
_cache_by_symbol: dict[str, dict[str, dict[str, Any]]] = {}


def _number(value: Any, *, allow_negative: bool = False) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    if not allow_negative and number <= 0:
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
    from valuation_ratios.ingest import latest_ratio_map

    try:
        folded = latest_ratio_map()
    except Exception:
        return None, {}

    reference_date = max(
        (str(pack.get("as_of") or "")[:10] for pack in folded.values()),
        default="",
    ) or None
    by_symbol: dict[str, dict[str, dict[str, Any]]] = {}
    for symbol, pack in folded.items():
        as_of = str(pack.get("as_of") or "")[:10]
        age = _days_between(as_of, reference_date or as_of) if as_of else None
        freshness = "FRESH" if age is not None and age <= FRESH_WITHIN_DAYS else "LATEST"
        metrics: dict[str, dict[str, Any]] = {}
        for metric in CURRENT_METRICS:
            value = _number(
                pack.get(metric),
                allow_negative=metric in {"roe", "roa", "roce"},
            )
            if value is None:
                continue
            metrics[metric] = {
                "value": value,
                "sector_value": _number(pack.get(f"{metric}_sector"), allow_negative=True),
                "as_of": as_of,
                "freshness": freshness,
                "source": "upstox",
            }
        if metrics:
            by_symbol[symbol] = metrics
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
