"""Living peer packs."""

from __future__ import annotations

from typing import Any

from peer_intelligence.peer_database.packs import (
    banks_india,
    consumer_internet,
    fmcg_india,
    it_services,
)

PACKS = {
    banks_india.PACK_ID: banks_india.pack,
    fmcg_india.PACK_ID: fmcg_india.pack,
    it_services.PACK_ID: it_services.pack,
    consumer_internet.PACK_ID: consumer_internet.pack,
}


def _maybe_filing_overlay(pack: dict[str, Any]) -> dict[str, Any]:
    """Soft-wire: Filing Intelligence upgrades seed panels → live filing panels."""
    try:
        from filing_intelligence.peer_sync import overlay_peer_series

        return overlay_peer_series(pack)
    except Exception:
        return pack


def all_packs() -> list[dict[str, Any]]:
    return [_maybe_filing_overlay(fn()) for fn in PACKS.values()]


def pack_by_id(pack_id: str) -> dict[str, Any] | None:
    fn = PACKS.get(pack_id)
    if not fn:
        return None
    return _maybe_filing_overlay(fn())
