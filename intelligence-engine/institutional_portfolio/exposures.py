"""Portfolio exposures — sector, country, industry, recommendation mix."""

from __future__ import annotations

from typing import Iterable, Sequence

from institutional_portfolio.portfolio_entities import ExposureRecord, HoldingRecord


def _bucket(holdings: Sequence[HoldingRecord], attr: str, dimension: str) -> list[ExposureRecord]:
    acc: dict[str, float] = {}
    for h in holdings:
        name = str(getattr(h, attr, None) or "Unknown")
        acc[name] = acc.get(name, 0.0) + float(h.weight or 0.0)
    rows = [
        ExposureRecord(dimension=dimension, name=name, weight=weight)
        for name, weight in acc.items()
    ]
    rows.sort(key=lambda r: r.weight, reverse=True)
    return rows


def compute_exposures(holdings: Sequence[HoldingRecord]) -> tuple[ExposureRecord, ...]:
    rows: list[ExposureRecord] = []
    rows.extend(_bucket(holdings, "sector", "sector"))
    rows.extend(_bucket(holdings, "industry", "industry"))
    rows.extend(_bucket(holdings, "country", "country"))
    rows.extend(_bucket(holdings, "recommendation", "recommendation"))
    return tuple(rows)


def exposures_by_dimension(
    exposures: Iterable[ExposureRecord], dimension: str
) -> list[ExposureRecord]:
    return [e for e in exposures if e.dimension == dimension]
