"""Allocation engine helpers — weights and target bands (no optimisation)."""

from __future__ import annotations

from typing import Any, Sequence

from institutional_portfolio.portfolio_entities import AllocationRecord, HoldingRecord


def _band(weight: float) -> str:
    w = float(weight or 0.0)
    if w >= 0.20:
        return "overweight"
    if w >= 0.10:
        return "core"
    if w >= 0.05:
        return "standard"
    if w > 0:
        return "satellite"
    return "none"


def build_allocations(holdings: Sequence[HoldingRecord]) -> tuple[AllocationRecord, ...]:
    rows: list[AllocationRecord] = []
    for h in holdings:
        rows.append(
            AllocationRecord(
                ticker=h.ticker,
                weight=float(h.weight),
                target_band=_band(h.weight),
                role="core" if h.weight >= 0.10 else "satellite",
            )
        )
    rows.sort(key=lambda a: a.weight, reverse=True)
    return tuple(rows)


def allocation_summary(allocations: Sequence[AllocationRecord]) -> dict[str, Any]:
    by_band: dict[str, float] = {}
    for a in allocations:
        by_band[a.target_band] = by_band.get(a.target_band, 0.0) + float(a.weight)
    return {
        "count": len(allocations),
        "by_band": by_band,
        "largest": allocations[0].to_dict() if allocations else None,
        "optimises": False,
    }
