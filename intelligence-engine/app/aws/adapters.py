"""Soft adapters over existing platforms — no new research logic."""

from __future__ import annotations

from typing import Any


def dump(obj: Any) -> dict[str, Any] | None:
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        try:
            return obj.model_dump(mode="json")
        except Exception:
            return obj.model_dump()
    if hasattr(obj, "__dict__"):
        return dict(obj.__dict__)
    return {"value": str(obj)}


def soft(fn, *args, default=None, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception:
        return default


def engine_state(svc: Any, *, symbol: str | None = None, as_of: str | None = None) -> dict[str, Any] | None:
    if svc is None:
        return None
    if symbol is not None:
        return dump(soft(svc.get_state, symbol, as_of=as_of))
    return dump(soft(svc.get_state, as_of=as_of))


def portfolio_weight(portfolio: dict[str, Any] | None, ticker: str) -> float | None:
    if not portfolio:
        return None
    t = ticker.upper()
    weights = portfolio.get("weights") or portfolio.get("positions") or {}
    if isinstance(weights, dict):
        for k, v in weights.items():
            if str(k).upper() == t:
                try:
                    return float(v if not isinstance(v, dict) else v.get("weight", v.get("w", 0)))
                except Exception:
                    return None
    if isinstance(weights, list):
        for row in weights:
            if isinstance(row, dict) and str(row.get("symbol") or row.get("ticker") or "").upper() == t:
                try:
                    return float(row.get("weight") or row.get("w") or 0)
                except Exception:
                    return None
    return None
