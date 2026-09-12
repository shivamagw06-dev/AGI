"""Production façades for the NSE trading equity universe."""

from __future__ import annotations

from typing import Any

from trading_universe.loader import dashboard, get_symbol, health, list_symbols, load_rows, search


def soft_slice_for_ask_agi(question: str = "", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Soft bind: if question names a tradable symbol, expose membership."""
    _ = payload
    q = (question or "").strip()
    hits = search(q, limit=5) if q else []
    h = health()
    return {
        "trading_universe": {
            "enabled": True,
            "count": h.get("count"),
            "version": h.get("version"),
            "matches": hits,
            "in_universe": bool(hits),
        }
    }


__all__ = [
    "dashboard",
    "get_symbol",
    "health",
    "list_symbols",
    "load_rows",
    "search",
    "soft_slice_for_ask_agi",
]
