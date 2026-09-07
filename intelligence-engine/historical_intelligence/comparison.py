"""Module 4 — Historical Comparison.

Companies are only compared over the window both of them were observed. Comparing
a twenty-year record against a three-year one and calling the winner would be a
statement about coverage, not about the businesses, so the overlap is computed
first and stated in the answer.
"""

from __future__ import annotations

import statistics
from typing import Any, Iterable, Optional

from historical_intelligence import coverage as coverage_engine
from institutional_warehouse import history
from institutional_warehouse.values import normalise_entity, to_date

# Below this, an overlap is too short to rank anyone on.
MIN_OVERLAP_DAYS = 200


def _overlap(covers: list[dict[str, Any]]) -> dict[str, Any]:
    firsts = [c["earliest"] for c in covers if c.get("earliest")]
    lasts = [c["latest"] for c in covers if c.get("latest")]
    if len(firsts) < 2 or len(lasts) < 2:
        return {"start": None, "end": None, "days": 0}
    start, end = max(firsts), min(lasts)
    if start > end:
        return {"start": None, "end": None, "days": 0}
    a, b = to_date(start), to_date(end)
    days = 0
    if a and b:
        from datetime import datetime

        days = (datetime.fromisoformat(b) - datetime.fromisoformat(a)).days
    return {"start": start, "end": end, "days": days}


def compare(symbols: Iterable[str], metric: str = "price") -> dict[str, Any]:
    names = [normalise_entity(s) for s in symbols if normalise_entity(s)]
    names = list(dict.fromkeys(names))
    if len(names) < 2:
        return {"ok": False, "error": "need_two_symbols", "symbols": names}
    if metric not in history.SERIES:
        return {"ok": False, "error": f"unknown_metric:{metric}",
                "available": sorted(history.SERIES)}

    covers = [coverage_engine.metric_coverage(name, metric) for name in names]
    missing = [c["symbol"] for c in covers if not c.get("observations")]
    present = [c for c in covers if c.get("observations")]

    out: dict[str, Any] = {
        "ok": True,
        "module": "comparison",
        "metric": metric,
        "symbols": names,
        "coverage": {c["symbol"]: c for c in covers},
        "without_history": missing,
        "confidence": min((c.get("confidence_score") or 0.0) for c in covers) if covers else 0.0,
    }

    if len(present) < 2:
        out["finding"] = (
            f"AGIB holds {metric} history for fewer than two of these companies "
            f"({', '.join(missing)} missing), so no comparison is made."
        )
        out["conclusions"] = []
        return out

    window = _overlap(present)
    spans = {c["symbol"]: c.get("window_label") for c in present}
    conclusions: list[str] = []

    if not window["start"] or window["days"] < MIN_OVERLAP_DAYS:
        out["overlap"] = window
        out["finding"] = (
            "These companies' observed histories barely overlap ("
            + "; ".join(f"{s}: {w}" for s, w in spans.items())
            + "), so a like-for-like comparison is not supported."
        )
        out["conclusions"] = [out["finding"]]
        return out

    rows: list[dict[str, Any]] = []
    for cover in present:
        series = history.series(cover["symbol"], metric, window="max",
                               start=window["start"], end=window["end"])
        points = [p for p in (series.get("points") or []) if p.get("value") is not None]
        if len(points) < 2:
            continue
        stats = series.get("stats") or {}
        rows.append({
            "symbol": cover["symbol"],
            "first": points[0]["value"],
            "last": points[-1]["value"],
            "from": points[0]["period"],
            "to": points[-1]["period"],
            "change_pct": stats.get("change_pct"),
            "cagr_pct": stats.get("cagr_pct"),
            "median": round(statistics.median([p["value"] for p in points]), 4),
            "observations": len(points),
        })

    if len(rows) < 2:
        out["overlap"] = window
        out["finding"] = (
            f"Too few observations inside the shared window ({window['start']} to "
            f"{window['end']}) to compare."
        )
        out["conclusions"] = [out["finding"]]
        return out

    key = "cagr_pct" if any(r.get("cagr_pct") is not None for r in rows) else "change_pct"
    ranked = sorted(rows, key=lambda r: (r.get(key) is None, -(r.get(key) or 0)))
    best, worst = ranked[0], ranked[-1]

    conclusions.append(
        f"Compared only over the window both were observed ({window['start']} to "
        f"{window['end']}), {best['symbol']} leads on {_label(metric)} at "
        f"{_fmt(best.get(key))}% versus {worst['symbol']} at {_fmt(worst.get(key))}%."
    )
    conclusions.append(
        "Median levels inside that window: "
        + ", ".join(f"{r['symbol']} {r['median']}" for r in ranked) + "."
    )
    if len(set(spans.values())) > 1:
        conclusions.append(
            "Full observed spans differ — "
            + "; ".join(f"{s}: {w}" for s, w in spans.items())
            + " — so the comparison deliberately ignores history held for one company "
              "and not the other."
        )
    else:
        conclusions.append(
            f"Both are observed over the same span ({next(iter(spans.values()))}), so the "
            "comparison uses each company's full history."
        )
    if missing:
        conclusions.append(f"No {metric} history held for {', '.join(missing)}.")

    out.update({
        "overlap": window,
        "rows": ranked,
        "ranking": [r["symbol"] for r in ranked],
        "ranked_on": key,
        "finding": conclusions[0],
        "conclusions": conclusions,
        "observation_window": f"{window['start']} to {window['end']}",
        "disclosure": (
            f"Comparison restricted to the shared observation window {window['start']} to "
            f"{window['end']}."
        ),
    })
    return out


def against_sector(symbol: str, metric: str = "pe") -> dict[str, Any]:
    """One company against the sector median priced on the same day."""
    from institutional_warehouse import store

    ticker = normalise_entity(symbol)
    cover = coverage_engine.metric_coverage(ticker, metric)
    if not cover.get("observations"):
        return {"ok": False, "error": "no_observations", "coverage": cover}
    rows = store.all_rows("historical_valuation", entity=ticker, limit=2000)
    dated = sorted([r for r in rows if to_date(r.get("date"))], key=lambda r: str(r["date"]))
    with_median = [r for r in dated if r.get("sector_median") and r.get(metric)]
    if not with_median:
        return {
            "ok": True,
            "module": "sector_comparison",
            "symbol": ticker,
            "observation_window": cover.get("window_label"),
            "finding": (
                f"AGIB holds {metric} observations for {ticker} but no same-day sector median, "
                "so no relative history is computed."
            ),
            "conclusions": [],
            "coverage": cover,
        }

    gaps = []
    for row in with_median:
        median = float(row["sector_median"])
        value = float(row[metric])
        if median:
            gaps.append({"date": row["date"], "gap_pct": round(100.0 * (value - median) / abs(median), 1)})
    latest = gaps[-1]
    average = round(statistics.fmean(g["gap_pct"] for g in gaps), 1)
    stance = "premium" if latest["gap_pct"] > 0 else "discount"
    return {
        "ok": True,
        "module": "sector_comparison",
        "symbol": ticker,
        "metric": metric,
        "observation_window": f"{gaps[0]['date']} to {latest['date']}",
        "observations": len(gaps),
        "latest_gap_pct": latest["gap_pct"],
        "average_gap_pct": average,
        "history": gaps[-40:],
        "finding": (
            f"{ticker} trades at a {abs(latest['gap_pct'])}% {stance} to its sector on "
            f"{_label(metric)} as of {latest['date']}, against an average "
            f"{'premium' if average > 0 else 'discount'} of {abs(average)}% across "
            f"{len(gaps)} observations from {gaps[0]['date']}."
        ),
        "conclusions": [],
        "coverage": cover,
    }


def _label(metric: str) -> str:
    from historical_intelligence.span_guard import _readable

    return _readable(metric)


def _fmt(value: Optional[float]) -> str:
    return "n/a" if value is None else f"{value:,.2f}".rstrip("0").rstrip(".")
