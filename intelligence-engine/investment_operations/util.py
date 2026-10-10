"""Shared helpers for Investment Operations Layer."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def as_float(v: Any) -> float | None:
    if v is None or isinstance(v, bool):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def priority_rank(p: str | None) -> int:
    order = ("Critical", "High", "Medium", "Low", "Monitor")
    try:
        return order.index(p or "Monitor")
    except ValueError:
        return len(order)


def soft_call(label: str, fn, *args, **kwargs) -> dict[str, Any]:
    try:
        out = fn(*args, **kwargs)
        if isinstance(out, dict):
            return {**out, "_soft": label, "_ok": True}
        return {"_soft": label, "_ok": True, "value": out}
    except Exception as exc:  # noqa: BLE001
        return {"_soft": label, "_ok": False, "error": f"{type(exc).__name__}:{str(exc)[:120]}"}


def default_universe() -> tuple[str, ...]:
    try:
        from opportunity_intelligence.schema import IC10_UNIVERSE

        return tuple(IC10_UNIVERSE)
    except Exception:
        return (
            "HDFCBANK",
            "RELIANCE",
            "TCS",
            "ETERNAL",
            "TATAMOTORS",
            "SUNPHARMA",
            "NTPC",
            "HAL",
            "ASIANPAINT",
            "ULTRACEMCO",
        )


def resolve_ticker(ticker: str) -> str:
    try:
        from company_memory.resolve import resolve_ticker as _r

        return _r(ticker)
    except Exception:
        key = (ticker or "").upper().replace(".NS", "").replace(".BO", "").strip()
        return {"TATAMOTORS": "TMPV", "ZOMATO": "ETERNAL"}.get(key, key)
