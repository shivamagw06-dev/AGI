"""Module 2 — Historical Valuation Intelligence.

Where does today's multiple sit against its own past, and did the market pay more
or less for the same earnings over time. Every answer names its window, because a
percentile computed over three years and one computed over twenty are different
claims wearing the same word.
"""

from __future__ import annotations

import statistics
from typing import Any, Optional

from historical_intelligence import coverage as coverage_engine
from historical_intelligence.span_guard import guard, qualify_extreme
from institutional_warehouse import history, store
from institutional_warehouse.values import to_date

MULTIPLES = ("pe", "pb", "ev_ebitda", "ev_sales", "price_sales", "dividend_yield")

# Below this many observations a percentile is arithmetic, not evidence.
MIN_OBSERVATIONS = 6


def analyse(symbol: str, metric: str = "pe", *,
            period: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    cover = coverage_engine.metric_coverage(symbol, metric)
    if not cover.get("ok"):
        return {"ok": False, **cover}

    asked = period or {"start": None, "end": None, "label": "the observed history",
                       "kind": "open", "asked": False}
    verdict = guard(cover, asked)
    out: dict[str, Any] = {
        "ok": True,
        "module": "valuation",
        "symbol": cover["symbol"],
        "metric": metric,
        "coverage": cover,
        "guard": verdict,
        "observation_window": cover.get("window_label"),
        "confidence": cover.get("confidence"),
    }
    if not verdict.get("may_conclude"):
        out["finding"] = verdict["disclosure"]
        out["conclusions"] = []
        return out

    series = history.series(cover["symbol"], metric, window="max")
    points = [p for p in (series.get("points") or []) if p.get("value") is not None]
    if len(points) < 2:
        out["finding"] = verdict["disclosure"]
        out["conclusions"] = []
        return out

    values = [p["value"] for p in points]
    latest = points[-1]
    median = round(statistics.median(values), 4)
    percentile = round(100.0 * sum(1 for v in values if v <= latest["value"]) / len(values), 1)
    premium = None
    if median:
        premium = round(100.0 * (latest["value"] - median) / abs(median), 1)
    lo = min(points, key=lambda p: p["value"])
    hi = max(points, key=lambda p: p["value"])
    qualifier = qualify_extreme(verdict, cover)

    conclusions: list[str] = []
    label = _label(metric)
    stance = "above" if (premium or 0) > 0 else ("below" if (premium or 0) < 0 else "in line with")
    conclusions.append(
        f"{label} is {_fmt(latest['value'])} against a median of {_fmt(median)} "
        f"{qualifier} — {abs(premium) if premium is not None else 0}% {stance} its own history."
    )

    if len(points) >= MIN_OBSERVATIONS:
        where = ("the cheaper end" if percentile <= 33 else
                 "the middle" if percentile <= 66 else "the more expensive end")
        conclusions.append(
            f"That places it in the {percentile}th percentile of {len(points)} observations, "
            f"{where} of the observed range ({_fmt(lo['value'])} in {lo['period']} to "
            f"{_fmt(hi['value'])} in {hi['period']})."
        )
    else:
        conclusions.append(
            f"Only {len(points)} observations are held, too few for a percentile to mean much; "
            f"the observed range is {_fmt(lo['value'])} to {_fmt(hi['value'])}."
        )

    rerating = _rerating(points)
    if rerating:
        conclusions.append(rerating["sentence"])

    peers = _peer_position(cover["symbol"], metric)
    if peers:
        conclusions.append(peers["sentence"])

    if not verdict.get("full_history_claim_allowed"):
        conclusions.append(
            "Earlier valuation observations are not held, so this is a statement about the "
            "observed window rather than the company's full history."
        )

    out.update({
        "finding": conclusions[0],
        "conclusions": conclusions,
        "latest": latest,
        "median": median,
        "percentile": percentile,
        "premium_to_own_median_pct": premium,
        "low": lo,
        "high": hi,
        "observations": len(points),
        "rerating": rerating,
        "peer_position": peers,
        "disclosure": verdict["disclosure"],
    })
    return out


def _rerating(points: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """Did the multiple expand or compress across the window, and by how much."""
    if len(points) < 4:
        return None
    half = len(points) // 2
    early = statistics.median([p["value"] for p in points[:half]])
    late = statistics.median([p["value"] for p in points[half:]])
    if not early:
        return None
    change = round(100.0 * (late - early) / abs(early), 1)
    if abs(change) < 10.0:
        return {
            "direction": "stable", "change_pct": change,
            "sentence": (
                f"The multiple has been broadly stable across the window: the median moved "
                f"{change}% between the earlier and later halves."
            ),
        }
    direction = "expansion" if change > 0 else "compression"
    return {
        "direction": direction,
        "change_pct": change,
        "early_median": round(early, 4),
        "late_median": round(late, 4),
        "sentence": (
            f"The market has re-rated the shares: median {'up' if change > 0 else 'down'} "
            f"{abs(change)}% from {round(early, 2)} in the earlier half of the window to "
            f"{round(late, 2)} in the later half — multiple {direction}."
        ),
    }


def _peer_position(symbol: str, metric: str) -> Optional[dict[str, Any]]:
    """Today's standing against the sector, from the same snapshot date."""
    if metric not in ("pe", "pb"):
        return None
    try:
        rows = store.all_rows("historical_valuation", entity=symbol, limit=5)
        if not rows:
            return None
        latest = sorted(rows, key=lambda r: str(r.get("date")))[-1]
        median = latest.get("sector_median")
        value = latest.get(metric)
        percentile = latest.get("percentile")
        if not median or not value:
            return None
        gap = round(100.0 * (value - median) / abs(median), 1)
        stance = "a premium to" if gap > 0 else "a discount to"
        sentence = (
            f"Against peers priced on {latest.get('date')}, the sector median {_label(metric)} "
            f"is {round(median, 2)}, so the shares trade at {stance} the sector of {abs(gap)}%."
        )
        if percentile is not None:
            sentence += f" Cross-sectional cheapness percentile: {percentile}."
        return {"sector_median": median, "gap_pct": gap, "percentile": percentile,
                "as_of": latest.get("date"), "sentence": sentence}
    except Exception:
        return None


def bands(symbol: str, metric: str = "pe") -> dict[str, Any]:
    """The quartile band a chart would draw, with its window attached."""
    cover = coverage_engine.metric_coverage(symbol, metric)
    if not cover.get("ok") or not cover.get("observations"):
        return {"ok": False, "error": "no_observations", "coverage": cover}
    series = history.series(cover["symbol"], metric, window="max")
    values = sorted(p["value"] for p in (series.get("points") or []) if p.get("value") is not None)
    if len(values) < 4:
        return {"ok": False, "error": "too_few_observations", "coverage": cover}
    quantile = statistics.quantiles(values, n=4)
    return {
        "ok": True,
        "symbol": cover["symbol"],
        "metric": metric,
        "observation_window": cover.get("window_label"),
        "observations": len(values),
        "min": values[0],
        "q1": round(quantile[0], 4),
        "median": round(quantile[1], 4),
        "q3": round(quantile[2], 4),
        "max": values[-1],
        "confidence": cover.get("confidence"),
    }


def _label(metric: str) -> str:
    from historical_intelligence.span_guard import _readable

    return _readable(metric).upper() if metric in ("pe", "pb") else _readable(metric).capitalize()


def _fmt(value: Optional[float]) -> str:
    if value is None:
        return "n/a"
    if abs(value) >= 1e7:
        return f"{value / 1e7:,.1f} cr"
    return f"{value:,.2f}".rstrip("0").rstrip(".")
