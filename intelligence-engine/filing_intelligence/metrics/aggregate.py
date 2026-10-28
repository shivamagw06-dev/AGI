"""Aggregate extracted facts into metric series."""

from __future__ import annotations

from typing import Any


def build_metric_series(facts: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    series: dict[str, dict[str, Any]] = {}
    for f in facts:
        if f.get("category") != "financial":
            continue
        if not isinstance(f.get("value"), (int, float)):
            continue
        metric = f["metric"]
        bucket = series.setdefault(
            metric,
            {
                "metric": metric,
                "unit": f.get("unit") or "",
                "points": {},
                "sources": {},
                "tiers": {},
                "validation": {},
            },
        )
        period = f.get("period") or "NA"
        # prefer higher-tier (lower number) / verified when conflict
        existing = bucket["points"].get(period)
        if existing is not None:
            prev_tier = bucket["tiers"].get(period, 99)
            if int(f.get("evidence_tier") or 99) > prev_tier:
                continue
        bucket["points"][period] = float(f["value"])
        bucket["sources"][period] = f.get("doc_id")
        bucket["tiers"][period] = f.get("evidence_tier")
        bucket["validation"][period] = f.get("validation_status")
    return series
