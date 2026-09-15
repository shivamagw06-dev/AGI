"""Module 1 — Trend Intelligence.

Turns a series into a statement about the business: did it compound, where did it
turn, and is the change structural or a wobble. Nothing is extrapolated: the
engine describes the observed window and stops at its edge.
"""

from __future__ import annotations

import statistics
from typing import Any, Optional

from historical_intelligence import coverage as coverage_engine
from historical_intelligence.span_guard import guard, qualify_extreme
from institutional_warehouse import history
from institutional_warehouse.values import to_date

# A leg has to move enough to be worth naming.
MATERIAL_CHANGE_PCT = 8.0
# Half a series either side before a turn counts as an inflection.
MIN_LEG_POINTS = 3


def _clean(points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [p for p in points if p.get("value") is not None]


def _cagr(first: float, last: float, years: Optional[float]) -> Optional[float]:
    if not years or years < 1 or first <= 0 or last <= 0:
        return None
    return round(((last / first) ** (1.0 / years) - 1.0) * 100.0, 2)


def _legs(points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Split the series where direction changes materially."""
    if len(points) < MIN_LEG_POINTS * 2:
        return []
    values = [p["value"] for p in points]
    window = max(2, len(values) // 8)
    smoothed = [
        statistics.fmean(values[max(0, i - window):i + window + 1])
        for i in range(len(values))
    ]
    legs: list[dict[str, Any]] = []
    start = 0
    direction = None
    for i in range(1, len(smoothed)):
        step = smoothed[i] - smoothed[i - 1]
        current = "up" if step > 0 else ("down" if step < 0 else direction)
        if direction is None:
            direction = current
            continue
        if current != direction and (i - start) >= MIN_LEG_POINTS:
            legs.append(_leg(points, start, i, direction))
            start, direction = i, current
    if direction and (len(points) - start) >= MIN_LEG_POINTS:
        legs.append(_leg(points, start, len(points) - 1, direction))
    return [leg for leg in legs if abs(leg["change_pct"] or 0.0) >= MATERIAL_CHANGE_PCT]


def _leg(points: list[dict[str, Any]], i: int, j: int, direction: Optional[str]) -> dict[str, Any]:
    a, b = points[i], points[j]
    change = None
    if a["value"]:
        change = round(100.0 * (b["value"] - a["value"]) / abs(a["value"]), 2)
    return {
        "from": a["period"], "to": b["period"], "direction": direction,
        "from_value": a["value"], "to_value": b["value"], "change_pct": change,
    }


def _consistency(points: list[dict[str, Any]]) -> Optional[float]:
    """Share of periods that moved with the overall direction."""
    if len(points) < 3:
        return None
    values = [p["value"] for p in points]
    overall = 1 if values[-1] >= values[0] else -1
    steps = [1 if b >= a else -1 for a, b in zip(values, values[1:])]
    agree = sum(1 for s in steps if s == overall)
    return round(100.0 * agree / len(steps), 1)


def analyse(symbol: str, metric: str, *, period: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Describe how one metric behaved across the observed window."""
    cover = coverage_engine.metric_coverage(symbol, metric)
    if not cover.get("ok"):
        return {"ok": False, **cover}

    asked = period or {"start": None, "end": None, "label": "the observed history",
                       "kind": "open", "asked": False}
    verdict = guard(cover, asked)
    result: dict[str, Any] = {
        "ok": True,
        "module": "trend",
        "symbol": cover["symbol"],
        "metric": metric,
        "coverage": cover,
        "guard": verdict,
        "observation_window": cover.get("window_label"),
        "confidence": cover.get("confidence"),
    }
    if not verdict.get("may_conclude"):
        result["finding"] = verdict["disclosure"]
        result["conclusions"] = []
        return result

    series = history.series(cover["symbol"], metric, window="max",
                            start=verdict.get("overlap_from") or asked.get("start"),
                            end=verdict.get("overlap_to") or asked.get("end"))
    points = _clean(series.get("points") or [])
    if len(points) < 2:
        result["finding"] = (
            f"Only {len(points)} {metric} observation(s) fall inside {verdict['window_label']}, "
            "which is not enough to describe a trend."
        )
        result["conclusions"] = []
        return result

    first, last = points[0], points[-1]
    stats = series.get("stats") or {}
    years = stats.get("years")
    cagr = stats.get("cagr_pct") or _cagr(first["value"], last["value"], years)
    legs = _legs(points)
    consistency = _consistency(points)
    lo = min(points, key=lambda p: p["value"])
    hi = max(points, key=lambda p: p["value"])

    conclusions: list[str] = []
    direction = "rose" if last["value"] > first["value"] else (
        "fell" if last["value"] < first["value"] else "was unchanged")
    headline = (
        f"{_label(metric)} {direction} from {_fmt(first['value'])} in {first['period']} "
        f"to {_fmt(last['value'])} in {last['period']}"
    )
    if cagr is not None:
        headline += f", compounding at {cagr}% a year"
    conclusions.append(headline + ".")

    # One leg spanning the window is a straight run, not a non-linear path.
    if len(legs) > 1:
        shape = "; ".join(
            f"{leg['direction']} {abs(leg['change_pct'])}% from {leg['from']} to {leg['to']}"
            for leg in legs[:4]
        )
        conclusions.append(f"The path was not linear: {shape}.")
        turns = [leg["from"] for leg in legs[1:]]
        if turns:
            conclusions.append("Direction changed around " + ", ".join(turns[:3]) + ".")
    elif len(legs) == 1 and legs[0]["direction"]:
        # Only narrate the leg when it agrees with the endpoints; a smoothed leg that
        # disagrees means the series is too noisy to describe as one move.
        endpoint_up = last["value"] >= first["value"]
        if (legs[0]["direction"] == "up") == endpoint_up:
            conclusions.append(
                f"The move ran in one direction throughout, {legs[0]['direction']} "
                f"{abs(legs[0]['change_pct'])}% end to end, without a material reversal."
            )

    if consistency is not None:
        if consistency >= 75:
            conclusions.append(
                f"{consistency}% of periods moved with the overall direction, which reads as a "
                "sustained trend rather than a series of reversals."
            )
        elif consistency <= 45:
            conclusions.append(
                f"Only {consistency}% of periods moved with the overall direction, so the change "
                "is better described as volatile than structural."
            )

    qualifier = qualify_extreme(verdict, cover)
    conclusions.append(
        f"The range {qualifier} runs from {_fmt(lo['value'])} ({lo['period']}) to "
        f"{_fmt(hi['value'])} ({hi['period']})."
    )

    result.update(
        {
            "finding": conclusions[0],
            "conclusions": conclusions,
            "first": first,
            "last": last,
            "cagr_pct": cagr,
            "years": years,
            "legs": legs,
            "inflection_points": [leg["from"] for leg in legs[1:]],
            "consistency_pct": consistency,
            "low": lo,
            "high": hi,
            "points": len(points),
            "disclosure": verdict["disclosure"],
        }
    )
    return result


def _label(metric: str) -> str:
    from historical_intelligence.span_guard import _readable

    return _readable(metric).capitalize()


def _fmt(value: Optional[float]) -> str:
    if value is None:
        return "n/a"
    if abs(value) >= 1e9:
        return f"{value / 1e7:,.0f} cr"
    if abs(value) >= 1e7:
        return f"{value / 1e7:,.1f} cr"
    if abs(value) >= 1000:
        return f"{value:,.0f}"
    return f"{value:,.2f}".rstrip("0").rstrip(".")


def extreme(symbol: str, metric: str, *, want: str = "low",
            period: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Answer 'when was it highest/lowest' without ever implying more history than exists."""
    cover = coverage_engine.metric_coverage(symbol, metric)
    if not cover.get("ok"):
        return {"ok": False, **cover}
    asked = period or {"start": None, "end": None, "label": "its full history",
                       "kind": "all_time", "asked": True}
    verdict = guard(cover, asked)
    out: dict[str, Any] = {
        "ok": True, "module": "extreme", "symbol": cover["symbol"], "metric": metric,
        "coverage": cover, "guard": verdict, "observation_window": cover.get("window_label"),
        "confidence": cover.get("confidence"),
    }
    if not verdict.get("may_conclude"):
        out["finding"] = verdict["disclosure"]
        out["conclusions"] = []
        return out

    series = history.series(cover["symbol"], metric, window="max")
    points = _clean(series.get("points") or [])
    if not points:
        out["finding"] = verdict["disclosure"]
        out["conclusions"] = []
        return out

    target = min(points, key=lambda p: p["value"]) if want == "low" else \
        max(points, key=lambda p: p["value"])
    latest = points[-1]
    values = [p["value"] for p in points]
    percentile = round(100.0 * sum(1 for v in values if v <= latest["value"]) / len(values), 1)
    qualifier = qualify_extreme(verdict, cover)
    word = "lowest" if want == "low" else "highest"

    conclusions = [
        f"{_label(metric)} was {word} at {_fmt(target['value'])} in {target['period']}, "
        f"{qualifier}.",
        f"Today it stands at {_fmt(latest['value'])}, in the {percentile}th percentile of "
        f"the {len(points)} observations held.",
    ]
    if not verdict.get("full_history_claim_allowed"):
        conclusions.append(
            "Because earlier observations are not held, this is not a claim about the "
            "company's full listing history."
        )

    out.update({
        "finding": conclusions[0], "conclusions": conclusions, "extreme": target,
        "latest": latest, "percentile": percentile, "points": len(points),
        "disclosure": verdict["disclosure"],
    })
    return out
