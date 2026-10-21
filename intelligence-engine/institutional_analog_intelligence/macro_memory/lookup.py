"""Macro / regime-scoped memory helpers."""

from __future__ import annotations

from typing import Any

from institutional_analog_intelligence.registry.index import list_memories


def macro_memories(*, regime: str | None = None) -> list[dict[str, Any]]:
    rows = [
        m
        for m in list_memories()
        if m.get("type")
        in {
            "previous_rate_cycle",
            "previous_inflation_cycle",
            "liquidity_cycle",
            "credit_cycle",
            "commodity_shock",
            "currency_shock",
            "market_panic",
            "recovery",
            "historical_analog",
        }
        or m.get("macro_regime")
    ]
    if regime:
        return [
            m
            for m in rows
            if regime in (m.get("macro_regime") or []) or m.get("market_regime") == regime
        ]
    return rows
