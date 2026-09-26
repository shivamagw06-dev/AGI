"""PRE-01 exposure helpers — sector / country rolls for risk objects."""

from __future__ import annotations

from typing import Any, Sequence

from institutional_portfolio.portfolio_entities import ExposureRecord, HoldingRecord


def sector_exposure_rows(
    holdings: Sequence[HoldingRecord],
    exposures: Sequence[ExposureRecord],
) -> tuple[dict[str, Any], ...]:
    sectors = [e for e in exposures if e.dimension == "sector"]
    if sectors:
        return tuple(
            {"dimension": "sector", "name": e.name, "weight": float(e.weight)}
            for e in sorted(sectors, key=lambda x: float(x.weight), reverse=True)
        )
    buckets: dict[str, float] = {}
    for h in holdings:
        key = (h.sector or "Unknown").strip() or "Unknown"
        buckets[key] = buckets.get(key, 0.0) + float(h.weight or 0.0)
    ordered = sorted(buckets.items(), key=lambda kv: kv[1], reverse=True)
    return tuple({"dimension": "sector", "name": n, "weight": float(w)} for n, w in ordered)


def country_exposure_rows(
    holdings: Sequence[HoldingRecord],
    exposures: Sequence[ExposureRecord],
) -> tuple[dict[str, Any], ...]:
    countries = [e for e in exposures if e.dimension == "country"]
    if countries:
        return tuple(
            {"dimension": "country", "name": e.name, "weight": float(e.weight)}
            for e in sorted(countries, key=lambda x: float(x.weight), reverse=True)
        )
    buckets: dict[str, float] = {}
    for h in holdings:
        key = (h.country or "IN").strip() or "IN"
        buckets[key] = buckets.get(key, 0.0) + float(h.weight or 0.0)
    ordered = sorted(buckets.items(), key=lambda kv: kv[1], reverse=True)
    return tuple({"dimension": "country", "name": n, "weight": float(w)} for n, w in ordered)
