"""Metric direction signals from warehouse / DME series (read-only)."""

from __future__ import annotations

from typing import Any

from financial_intelligence.trends import normalize_series


def metric_signal(series: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    """Latest vs prior direction for a metric series."""
    rows = normalize_series(series or [])
    if len(rows) < 2:
        if len(rows) == 1:
            return {
                "metric": rows[0].get("metric"),
                "direction": "unknown",
                "pct_change": None,
                "latest": rows[0],
                "prior": None,
                "history_n": 1,
                "evidence_ids": _ids(rows[0]),
                "validation_status": rows[0].get("validation_status"),
                "available": True,
                "comparable": False,
            }
        return None
    prior, latest = rows[-2], rows[-1]
    curr, prev = float(latest["value"]), float(prior["value"])
    if prev == 0:
        pct = None
        direction = "up" if curr > 0 else ("down" if curr < 0 else "flat")
    else:
        pct = round(100.0 * (curr - prev) / abs(prev), 4)
        if abs(pct) < 0.5:
            direction = "flat"
        else:
            direction = "up" if pct > 0 else "down"
    return {
        "metric": latest.get("metric") or prior.get("metric"),
        "direction": direction,
        "pct_change": pct,
        "latest": latest,
        "prior": prior,
        "history_n": len(rows),
        "evidence_ids": _ids(latest, prior),
        "validation_status": latest.get("validation_status") or prior.get("validation_status"),
        "available": True,
        "comparable": True,
        "reporting_period": latest.get("period"),
    }


def _ids(*rows: dict[str, Any] | None) -> list[str]:
    out: list[str] = []
    for r in rows:
        if not r:
            continue
        eid = r.get("validation_id") or r.get("fact_key")
        if eid and str(eid) not in out:
            out.append(str(eid))
    return out


def build_signal_map(series_map: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for metric, series in (series_map or {}).items():
        sig = metric_signal(series)
        if sig:
            sig["metric"] = metric
            out[metric] = sig
    return out


def check_expectation(signal: dict[str, Any] | None, expected: str) -> str:
    """Return support | conflict | insufficient for one metric expectation."""
    if not signal or not signal.get("comparable"):
        return "insufficient"
    direction = signal.get("direction") or "unknown"
    if expected == "up":
        if direction == "up":
            return "support"
        if direction == "down":
            return "conflict"
        return "partial"  # flat
    if expected == "down":
        if direction == "down":
            return "support"
        if direction == "up":
            return "conflict"
        return "partial"
    if expected == "down_or_flat":
        if direction in {"down", "flat"}:
            return "support"
        if direction == "up":
            return "conflict"
        return "insufficient"
    if expected == "up_or_flat":
        if direction in {"up", "flat"}:
            return "support"
        if direction == "down":
            return "conflict"
        return "insufficient"
    if expected == "present_positive":
        latest = (signal.get("latest") or {}).get("value")
        if isinstance(latest, (int, float)) and latest > 0:
            return "support"
        return "conflict"
    return "insufficient"
