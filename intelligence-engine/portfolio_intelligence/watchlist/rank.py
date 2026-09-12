"""Watchlist engine — research / monitor / reduction priorities (no orders)."""

from __future__ import annotations

from typing import Any


def rank_watchlist(
    watchlist: list[dict[str, Any]] | None,
    *,
    holdings: list[dict[str, Any]],
    concentration: dict[str, Any],
    impact: dict[str, Any] | None,
    candidate: str | None,
) -> dict[str, Any]:
    held = {str(h.get("ticker")).upper(): h for h in holdings}
    additions = list(watchlist or [])
    if candidate and candidate.upper() not in {a.get("ticker") for a in additions}:
        additions = [
            {
                "ticker": candidate.upper(),
                "priority": "research",
                "note": f"Candidate impact: {(impact or {}).get('net_portfolio_effect')}",
            },
            *additions,
        ]

    reductions = []
    top = (concentration.get("top_holding") or {}).get("ticker")
    if top and float((concentration.get("top_holding") or {}).get("weight") or 0) >= 0.10:
        reductions.append(
            {
                "ticker": top,
                "priority": "monitor",
                "note": "Top weight near single-name budget — monitor concentration",
            }
        )
    # Low conviction names
    for h in holdings:
        if str(h.get("conviction") or "").lower() == "low":
            reductions.append(
                {
                    "ticker": h.get("ticker"),
                    "priority": "research",
                    "note": "Low conviction holding — research retention thesis",
                }
            )

    exits: list[dict[str, Any]] = []  # never auto-exit

    return {
        "potential_additions": additions[:8],
        "potential_reductions": reductions[:8],
        "potential_exits": exits,
        "research_priority": [a for a in additions if a.get("priority") == "research"][:5],
        "monitoring_priority": [
            *(a for a in additions if a.get("priority") == "monitor"),
            *reductions,
        ][:8],
        "held_count": len(held),
        "never_orders": True,
    }
