"""Revision intelligence — upgrades/downgrades from stored expectations only."""

from __future__ import annotations

from typing import Any

from knowledge_factory.market_expectations_intelligence.schema import IMEI_VERSION, UNKNOWN


def build_revision_records(expectations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Pair sequential guidance/forecast revisions per entity+metric+period."""
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for e in expectations:
        if e.get("kind") == "actual":
            continue
        if e.get("forecast_value") == UNKNOWN:
            continue
        key = (
            str(e.get("entity") or "").upper(),
            str(e.get("metric") or "").lower(),
            str(e.get("period") or ""),
        )
        groups.setdefault(key, []).append(e)

    out: list[dict[str, Any]] = []
    for (entity, metric, period), rows in groups.items():
        rows = sorted(rows, key=lambda x: (x.get("revision_sequence", 0), x.get("available_from") or ""))
        if len(rows) < 2:
            continue
        for prev, cur in zip(rows, rows[1:]):
            try:
                a = float(prev.get("forecast_value"))
                b = float(cur.get("forecast_value"))
            except (TypeError, ValueError):
                continue
            delta = b - a
            pct = (delta / abs(a)) if a != 0 else 0.0
            direction = "upgrade" if delta > 0 else ("downgrade" if delta < 0 else "unchanged")
            out.append(
                {
                    "revision_id": f"REV-{cur.get('expectation_id')}",
                    "entity": entity,
                    "metric": metric,
                    "period": period,
                    "from_expectation_id": prev.get("expectation_id"),
                    "to_expectation_id": cur.get("expectation_id"),
                    "from_value": a,
                    "to_value": b,
                    "magnitude": round(delta, 6),
                    "magnitude_pct": round(pct, 6),
                    "direction": direction,
                    "revision_velocity": "sequential_observed",
                    "available_from": cur.get("available_from"),
                    "confidence": min(
                        float(prev.get("confidence") or 0),
                        float(cur.get("confidence") or 0),
                    ),
                    "source": cur.get("source"),
                    "version": IMEI_VERSION,
                    "fabricated": False,
                    "prediction": False,
                }
            )
    return out
