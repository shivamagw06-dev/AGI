"""Surprise intelligence — actual vs stored expectations only. No predictions."""

from __future__ import annotations

import hashlib
from typing import Any

from knowledge_factory.market_expectations_intelligence.schema import IMEI_VERSION, UNKNOWN


def compute_surprises(expectations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """For each actual, compare to latest pre-available expectation for same entity/metric/period."""
    actuals = [e for e in expectations if e.get("kind") == "actual" and e.get("forecast_value") != UNKNOWN]
    forecasts = [
        e
        for e in expectations
        if e.get("kind") in ("guidance", "internal_forecast", "consensus_proxy", "licensed_consensus")
        and e.get("forecast_value") != UNKNOWN
    ]

    out: list[dict[str, Any]] = []
    for act in actuals:
        entity = str(act.get("entity") or "").upper()
        metric = str(act.get("metric") or "").lower()
        period = str(act.get("period") or "")
        act_from = str(act.get("available_from") or "")
        try:
            actual_val = float(act.get("forecast_value"))
        except (TypeError, ValueError):
            continue

        # Expectations available strictly before or on actual date, prefer internal/guidance
        cands = [
            f
            for f in forecasts
            if str(f.get("entity") or "").upper() == entity
            and str(f.get("metric") or "").lower() == metric
            and str(f.get("period") or "") == period
            and str(f.get("available_from") or "") <= act_from
            and f.get("kind") != "actual"
        ]
        if not cands:
            continue
        # Prefer agib_internal_forecast / guidance latest by available_from
        cands.sort(key=lambda x: (x.get("available_from") or "", x.get("revision_sequence", 0)))
        exp = cands[-1]
        try:
            expected_val = float(exp.get("forecast_value"))
        except (TypeError, ValueError):
            continue
        if expected_val == 0:
            continue

        delta = actual_val - expected_val
        pct = delta / abs(expected_val)
        beat_miss = "beat" if delta > 0 else ("miss" if delta < 0 else "inline")
        sid = "SUR-" + hashlib.sha256(
            f"{act.get('expectation_id')}|{exp.get('expectation_id')}".encode()
        ).hexdigest()[:14].upper()

        out.append(
            {
                "surprise_id": sid,
                "entity": entity,
                "metric": metric,
                "period": period,
                "expected_value": expected_val,
                "actual_value": actual_val,
                "difference": round(delta, 6),
                "surprise_pct": round(pct, 6),
                "beat_miss": beat_miss,
                "magnitude": abs(round(pct, 6)),
                "expectation_id": exp.get("expectation_id"),
                "actual_expectation_id": act.get("expectation_id"),
                "expectation_source": exp.get("source"),
                "actual_source": act.get("source"),
                "available_from": act_from,
                "historical_percentile": UNKNOWN,  # filled in corpus pass if enough history
                "persistence": UNKNOWN,
                "version": IMEI_VERSION,
                "fabricated": False,
                "prediction": False,
                "note": "Observed comparison against stored Phase-1 expectation only.",
            }
        )

    # Beat/miss history + percentile within metric
    by_metric: dict[str, list[dict[str, Any]]] = {}
    for s in out:
        by_metric.setdefault(s["metric"], []).append(s)
    for metric, rows in by_metric.items():
        pcts = sorted(r["surprise_pct"] for r in rows)
        for r in rows:
            below = sum(1 for p in pcts if p <= r["surprise_pct"])
            r["historical_percentile"] = round(100.0 * below / len(pcts), 2) if pcts else UNKNOWN

    # Persistence: consecutive beats per entity
    by_entity: dict[str, list[dict[str, Any]]] = {}
    for s in out:
        by_entity.setdefault(s["entity"], []).append(s)
    for entity, rows in by_entity.items():
        rows = sorted(rows, key=lambda x: x.get("available_from") or "")
        streak = 0
        for r in rows:
            if r["beat_miss"] == "beat":
                streak += 1
            else:
                streak = 0
            r["persistence"] = streak
            # entity-level beat history
            r["beat_miss_history"] = [x["beat_miss"] for x in rows]

    return out
