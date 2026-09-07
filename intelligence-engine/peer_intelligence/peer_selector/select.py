"""Select analysis universe for a ticker (direct vs global)."""

from __future__ import annotations

from typing import Any

from peer_intelligence.resolver.resolve import resolve_peers


def select_universe(ticker: str, *, include_global: bool = True) -> dict[str, Any]:
    resolved = resolve_peers(ticker)
    if not resolved.get("resolved"):
        return resolved
    universe = list(resolved.get("direct_universe") or [])
    if include_global:
        for g in resolved.get("global_universe") or []:
            if g not in universe:
                universe.append(g)
    # ensure subject included
    t = resolved["ticker"]
    if t not in universe:
        universe = [t] + universe
    return {
        **resolved,
        "analysis_universe": universe,
        "include_global": include_global,
    }
