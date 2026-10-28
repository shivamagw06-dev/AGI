"""Time-series engine from filing facts — quarterly/annual/multi-year."""

from __future__ import annotations

from statistics import median
from typing import Any

from filing_intelligence.metrics.aggregate import build_metric_series


def _period_key(period: str) -> tuple[int, int, int]:
    """Sort key: FY26 < Q1FY27 < Q2FY27 …"""
    p = (period or "").upper().strip()
    if p.startswith("Q") and "FY" in p:
        try:
            q = int(p[1])
            fy = int(p.split("FY", 1)[1][:2])
            return (fy, q, 0)
        except Exception:
            return (0, 0, 0)
    if p.startswith("FY"):
        try:
            fy = int(p[2:4])
            return (fy, 0, 0)
        except Exception:
            return (0, 0, 0)
    return (0, 0, 0)


def history_from_facts(facts: list[dict[str, Any]]) -> dict[str, Any]:
    series = build_metric_series(facts)
    out = []
    for metric, s in series.items():
        pts = s["points"]
        if not pts:
            continue
        items = sorted(pts.items(), key=lambda kv: _period_key(kv[0]))
        vals = [v for _, v in items]
        trend = _trend(vals)
        out.append(
            {
                "metric": metric,
                "unit": s["unit"],
                "points": {k: pts[k] for k, _ in items},
                "sources": s["sources"],
                "tiers": s["tiers"],
                "validation": s["validation"],
                "latest_period": items[-1][0],
                "latest": items[-1][1],
                "min": min(vals),
                "max": max(vals),
                "average": round(sum(vals) / len(vals), 4),
                "median": round(float(median(vals)), 4),
                "3y_avg": round(sum(vals[-3:]) / min(3, len(vals)), 4),
                "5y_avg": round(sum(vals[-5:]) / min(5, len(vals)), 4),
                "10y_avg": round(sum(vals) / len(vals), 4),
                "trend": trend["label"],
                "acceleration": trend["acceleration"],
                "turning_point": trend["turning_point"],
                "historical_percentile_latest": _hist_pct(vals),
                "origin": "filing_intelligence",
            }
        )
    return {"series": out, "count": len(out)}


def _trend(vals: list[float]) -> dict[str, Any]:
    if len(vals) < 2:
        return {"label": "stable", "acceleration": False, "turning_point": False}
    delta = vals[-1] - vals[0]
    label = "stable"
    if abs(delta) > 0.05 * (abs(vals[0]) + 1e-9):
        label = "improving" if delta > 0 else "deteriorating"
    accel = False
    turning = False
    if len(vals) >= 3:
        s1 = vals[-2] - vals[-3]
        s2 = vals[-1] - vals[-2]
        accel = (s2 > s1 > 0) or (s2 < s1 < 0)
        turning = (s1 > 0 >= s2) or (s1 < 0 <= s2)
        if accel and label == "improving":
            label = "accelerating"
        elif label == "deteriorating" and s2 > s1:
            label = "decelerating"
    return {"label": label, "acceleration": accel, "turning_point": turning}


def _hist_pct(vals: list[float]) -> float:
    if len(vals) < 2:
        return 50.0
    latest = vals[-1]
    beat = sum(1 for v in vals[:-1] if latest > v)
    return round(100.0 * beat / (len(vals) - 1), 1)
