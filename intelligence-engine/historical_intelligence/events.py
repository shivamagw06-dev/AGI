"""Module 3 — Corporate Event Timeline.

Aligns what the company did with what the shares did around it. The engine states
the move it observed and stops short of asserting the event caused it: with daily
closes and a dated action, association is what the evidence supports.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from historical_intelligence import coverage as coverage_engine
from historical_intelligence.span_guard import guard
from institutional_warehouse import store
from institutional_warehouse.values import to_date, to_number

# Trading window either side of an event used to describe the reaction.
REACTION_DAYS = 30


def _price_series(symbol: str) -> list[dict[str, Any]]:
    rows = store.all_rows("daily_market_history", entity=symbol, limit=20000)
    points = []
    for row in rows:
        date, close = to_date(row.get("date")), to_number(row.get("close"))
        if date and close is not None:
            points.append({"date": date, "close": close})
    return sorted(points, key=lambda p: p["date"])


def _nearest(points: list[dict[str, Any]], target: str, *, before: bool) -> Optional[dict[str, Any]]:
    candidates = [p for p in points if (p["date"] <= target if before else p["date"] >= target)]
    if not candidates:
        return None
    return candidates[-1] if before else candidates[0]


def _reaction(points: list[dict[str, Any]], event_date: str) -> Optional[dict[str, Any]]:
    if not points:
        return None
    before = _nearest(points, event_date, before=True)
    horizon = (datetime.fromisoformat(event_date) + timedelta(days=REACTION_DAYS)).date().isoformat()
    after = _nearest(points, horizon, before=True)
    if not before or not after or after["date"] <= before["date"] or not before["close"]:
        return None
    change = round(100.0 * (after["close"] - before["close"]) / before["close"], 2)
    return {"from": before, "to": after, "change_pct": change, "horizon_days": REACTION_DAYS}


def timeline(symbol: str, *, period: Optional[dict[str, Any]] = None,
             limit: int = 40) -> dict[str, Any]:
    """Chronological events with the price move observed around each."""
    cover = coverage_engine.metric_coverage(symbol, "price")
    if not cover.get("ok"):
        return {"ok": False, **cover}
    ticker = cover["symbol"]

    asked = period or {"start": None, "end": None, "label": "the observed history",
                       "kind": "open", "asked": False}
    verdict = guard(cover, asked)

    actions = store.all_rows("corporate_actions", entity=ticker, limit=2000)
    research = store.all_rows("research_timeline", entity=ticker, limit=500)
    prices = _price_series(ticker)

    entries: list[dict[str, Any]] = []
    for row in actions:
        date = to_date(row.get("action_date"))
        if not date:
            continue
        entries.append({
            "date": date,
            "kind": str(row.get("action_type") or "action"),
            "headline": _action_headline(row),
            "source": row.get("source"),
        })
    for row in research:
        date = to_date(row.get("date"))
        if not date:
            continue
        entries.append({
            "date": date,
            "kind": "research",
            "headline": str(row.get("event") or "").strip() or "research note",
            "detail": str(row.get("results") or row.get("management") or "").strip() or None,
            "source": row.get("source"),
        })

    start, end = asked.get("start"), asked.get("end")
    if start:
        entries = [e for e in entries if e["date"] >= start]
    if end:
        entries = [e for e in entries if e["date"] <= end]
    entries.sort(key=lambda e: e["date"], reverse=True)
    entries = entries[: max(1, int(limit))]

    for entry in entries:
        reaction = _reaction(prices, entry["date"])
        if reaction:
            entry["price_before"] = reaction["from"]["close"]
            entry["price_after"] = reaction["to"]["close"]
            entry["move_pct"] = reaction["change_pct"]
            entry["move_window_days"] = reaction["horizon_days"]

    conclusions: list[str] = []
    if not entries:
        conclusions.append(
            f"AGIB holds no corporate events for {ticker} inside {verdict.get('window_label')}."
        )
    else:
        kinds: dict[str, int] = {}
        for entry in entries:
            kinds[entry["kind"]] = kinds.get(entry["kind"], 0) + 1
        shape = ", ".join(f"{count} {kind}" for kind, count in
                          sorted(kinds.items(), key=lambda kv: -kv[1])[:4])
        conclusions.append(
            f"{len(entries)} events observed for {ticker} between {entries[-1]['date']} and "
            f"{entries[0]['date']}: {shape}."
        )
        moved = [e for e in entries if e.get("move_pct") is not None]
        if moved:
            biggest = max(moved, key=lambda e: abs(e["move_pct"]))
            conclusions.append(
                f"The largest move around an event was {biggest['move_pct']}% in the "
                f"{biggest['move_window_days']} days after {biggest['headline']} "
                f"({biggest['date']}). The warehouse records the move alongside the event; it "
                "does not establish that the event caused it."
            )
        dividends = [e for e in entries if e["kind"] == "dividend"]
        if len(dividends) >= 3:
            conclusions.append(
                f"Dividends were declared in {len(dividends)} of the observed periods, which "
                "reads as a continuing distribution policy rather than a one-off."
            )

    return {
        "ok": True,
        "module": "events",
        "symbol": ticker,
        "coverage": cover,
        "guard": verdict,
        "observation_window": cover.get("window_label"),
        "events": entries,
        "event_count": len(entries),
        "finding": conclusions[0] if conclusions else "",
        "conclusions": conclusions,
        "confidence": cover.get("confidence"),
        "disclosure": verdict["disclosure"],
    }


def _action_headline(row: dict[str, Any]) -> str:
    kind = str(row.get("action_type") or "action")
    if kind == "dividend" and row.get("dividend") is not None:
        return f"dividend of {row['dividend']}"
    if kind == "split" and row.get("split"):
        return f"stock split {row['split']}"
    detail = str(row.get("details") or "").strip()
    if detail and len(detail) < 90:
        return detail
    return kind.replace("_", " ")


def around(symbol: str, period: dict[str, Any]) -> dict[str, Any]:
    """What happened to the shares during a named period such as COVID."""
    cover = coverage_engine.metric_coverage(symbol, "price")
    if not cover.get("ok"):
        return {"ok": False, **cover}
    verdict = guard(cover, period)
    out: dict[str, Any] = {
        "ok": True, "module": "period", "symbol": cover["symbol"], "coverage": cover,
        "guard": verdict, "observation_window": cover.get("window_label"),
        "confidence": cover.get("confidence"), "disclosure": verdict["disclosure"],
    }
    if not verdict.get("may_conclude"):
        out["finding"] = verdict["disclosure"]
        out["conclusions"] = []
        return out

    prices = _price_series(cover["symbol"])
    start = verdict.get("overlap_from") or period.get("start")
    end = verdict.get("overlap_to") or period.get("end")
    inside = [p for p in prices if (not start or p["date"] >= start) and (not end or p["date"] <= end)]
    if len(inside) < 2:
        out["finding"] = (
            f"Only {len(inside)} price observation(s) fall inside {period.get('label')}, "
            "which is not enough to describe what happened."
        )
        out["conclusions"] = []
        return out

    first, last = inside[0], inside[-1]
    low = min(inside, key=lambda p: p["close"])
    high = max(inside, key=lambda p: p["close"])
    change = round(100.0 * (last["close"] - first["close"]) / first["close"], 2)
    drawdown = round(100.0 * (low["close"] - high["close"]) / high["close"], 2) \
        if high["close"] else None

    conclusions = [
        f"Through {period.get('label')} ({first['date']} to {last['date']}) the shares moved "
        f"{change}%, from {first['close']:,.2f} to {last['close']:,.2f}.",
        f"The range inside that period ran {low['close']:,.2f} ({low['date']}) to "
        f"{high['close']:,.2f} ({high['date']}).",
    ]
    if drawdown is not None and drawdown < -10:
        conclusions.append(
            f"Peak-to-trough drawdown inside the period was {drawdown}%."
        )
    out.update({
        "finding": conclusions[0], "conclusions": conclusions, "change_pct": change,
        "low": low, "high": high, "observations": len(inside),
        "period": {"start": start, "end": end, "label": period.get("label")},
    })
    return out
