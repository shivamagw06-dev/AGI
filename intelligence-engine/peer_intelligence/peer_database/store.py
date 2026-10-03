"""Peer database store — living packs index."""

from __future__ import annotations

from typing import Any

from peer_intelligence.peer_database.packs import all_packs, pack_by_id

_ALIASES = {
    "HDFC": "HDFCBANK",
    "NESTLE": "NESTLEIND",
    "HUL": "HINDUNILVR",
    "ZOMATO": "ETERNAL",
}


def normalize_ticker(ticker: str) -> str:
    t = ticker.upper().replace(".NS", "").replace(".BO", "").strip()
    return _ALIASES.get(t, t)


def list_packs() -> list[dict[str, Any]]:
    return [
        {
            "pack_id": p["pack_id"],
            "sector": p["sector"],
            "direct_universe": p["direct_universe"],
            "global_universe": p["global_universe"],
            "series_count": len(p.get("series") or []),
            "missing": p.get("missing") or [],
        }
        for p in all_packs()
    ]


def get_pack(pack_id: str) -> dict[str, Any] | None:
    return pack_by_id(pack_id)


def find_pack_for_ticker(ticker: str) -> dict[str, Any] | None:
    t = normalize_ticker(ticker)
    for p in all_packs():
        ids = {i["ticker"] for i in p.get("identities") or []}
        if t in ids:
            return p
    return None


def identity(ticker: str) -> dict[str, Any] | None:
    t = normalize_ticker(ticker)
    pack = find_pack_for_ticker(t)
    if not pack:
        return None
    for i in pack.get("identities") or []:
        if i["ticker"] == t:
            return i
    return None
