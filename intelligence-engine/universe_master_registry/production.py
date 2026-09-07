"""Production façades for the Universe Master Registry."""

from __future__ import annotations

from typing import Any

from universe_master_registry.registry import (
    UNIVERSE_MASTER_VERSION,
    build_company_row,
    dashboard,
    get_company,
    list_registry,
)


def health() -> dict[str, Any]:
    d = dashboard()
    return {
        "ok": True,
        "version": UNIVERSE_MASTER_VERSION,
        "trading_universe_count": d.get("trading_universe_count"),
        "index_summary": d.get("index_summary"),
    }


__all__ = ["build_company_row", "dashboard", "get_company", "health", "list_registry"]
