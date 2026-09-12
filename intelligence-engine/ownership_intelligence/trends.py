"""QoQ analytics and rolling ownership trends — analytical facts only."""

from __future__ import annotations

from typing import Any

DELTA_FIELDS = (
    "promoter",
    "public",
    "fii",
    "dii",
    "mutual_funds",
    "insurance",
    "banks",
    "pension",
    "aif",
    "employee_trusts",
    "promoter_pledge_pct",
)


def _f(v: Any) -> float | None:
    try:
        if v is None:
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def qoq_deltas(current: dict[str, Any] | None, previous: dict[str, Any] | None) -> dict[str, Any]:
    cur = current or {}
    prev = previous or {}
    out: dict[str, Any] = {
        "as_of": cur.get("period_end"),
        "prev_as_of": prev.get("period_end"),
        "available": bool(cur and prev),
        "deltas_pp": {},
    }
    if not out["available"]:
        return out
    for field in DELTA_FIELDS:
        a, b = _f(cur.get(field)), _f(prev.get(field))
        if a is not None and b is not None:
            out["deltas_pp"][field] = round(a - b, 4)
    return out


def rolling_trend(history: list[dict[str, Any]], field: str, *, windows: int = 4) -> dict[str, Any]:
    """Newest-first history → trend for one field over up to `windows` quarters."""
    vals = []
    for row in history[:windows]:
        v = _f(row.get(field))
        if v is not None:
            vals.append({"period_end": row.get("period_end"), "value": v})
    if len(vals) < 2:
        return {"field": field, "direction": "insufficient_history", "change_pp": None, "points": vals}
    change = round(vals[0]["value"] - vals[-1]["value"], 4)
    if change > 0.25:
        direction = "increasing"
    elif change < -0.25:
        direction = "decreasing"
    else:
        direction = "stable"
    return {
        "field": field,
        "direction": direction,
        "change_pp": change,
        "window_quarters": len(vals),
        "points": vals,
    }


def build_qoq_series(history: list[dict[str, Any]], *, limit: int = 8) -> list[dict[str, Any]]:
    series = []
    for i in range(min(limit, max(0, len(history) - 1))):
        series.append(qoq_deltas(history[i], history[i + 1]))
    return series
