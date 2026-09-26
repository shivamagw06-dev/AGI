"""Ticker normalisation for Company Memory."""

from __future__ import annotations

from company_memory.schema import TICKER_ALIASES


def resolve_ticker(ticker: str) -> str:
    key = (ticker or "").upper().replace(".NS", "").replace(".BO", "").strip()
    return TICKER_ALIASES.get(key, key)


def display_ticker(ticker: str) -> str:
    key = (ticker or "").upper().replace(".NS", "").replace(".BO", "").strip()
    # Prefer human-facing names for renamed franchises
    if key == "TMPV":
        return "TATAMOTORS"
    if key == "ETERNAL":
        return "ETERNAL"
    return key
