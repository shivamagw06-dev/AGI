"""Market breadth from warehouse price history."""

from __future__ import annotations

from typing import Any, Optional


def _session_breadth(
    latest_rows: dict[str, dict[str, Any]], prior_rows: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Breadth for one consecutive-session pair, without any market label."""
    advancing = declining = unchanged = 0
    returns: list[float] = []
    for sym, row in latest_rows.items():
        prev = prior_rows.get(sym)
        if not prev:
            continue
        try:
            close = float(row.get("close") or row.get("adjusted_close") or 0)
            old = float(prev.get("close") or prev.get("adjusted_close") or 0)
        except (TypeError, ValueError):
            continue
        if old <= 0:
            continue
        chg = 100.0 * (close - old) / old
        returns.append(chg)
        if chg > 0.05:
            advancing += 1
        elif chg < -0.05:
            declining += 1
        else:
            unchanged += 1
    ratio = advancing / max(1, advancing + declining)
    heatmap = "Neutral"
    if ratio >= 0.65:
        heatmap = "Strong Bullish"
    elif ratio >= 0.55:
        heatmap = "Bullish"
    elif ratio <= 0.35:
        heatmap = "Strong Bearish"
    elif ratio <= 0.45:
        heatmap = "Bearish"
    return {
        "advancing": advancing,
        "declining": declining,
        "unchanged": unchanged,
        "average_return_pct": round(sum(returns) / len(returns), 2) if returns else None,
        "heatmap": heatmap,
        "sample_size": len(returns),
    }


def market_breadth(*, sample_limit: int = 3000) -> dict[str, Any]:
    from institutional_warehouse import db, store

    table = db.physical_table("daily_market_history")
    dates = db.query(f'SELECT DISTINCT "date" AS d FROM {table} ORDER BY d DESC LIMIT 4')
    if len(dates) < 2:
        return {"ok": False, "error": "insufficient_price_history", "advancing": 0, "declining": 0}

    date_values = [row["d"] for row in dates]
    rows_by_date = {
        day: {
            str(row.get("symbol") or "").upper(): row
            for row in store.fetch("daily_market_history", filters={"date": day}, limit=sample_limit)["rows"]
        }
        for day in date_values
    }
    latest, prior = date_values[0], date_values[1]
    current = _session_breadth(rows_by_date[latest], rows_by_date[prior])
    sessions = []
    for current_day, previous_day in zip(date_values, date_values[1:]):
        item = _session_breadth(rows_by_date[current_day], rows_by_date[previous_day])
        sessions.append({"date": current_day, **item})

    advancing, declining, unchanged = current["advancing"], current["declining"], current["unchanged"]
    avg_ret = current["average_return_pct"]
    returns = []
    for sym, row in rows_by_date[latest].items():
        prev = rows_by_date[prior].get(sym)
        try:
            if prev:
                returns.append(100.0 * (float(row.get("close") or row.get("adjusted_close") or 0) / float(prev.get("close") or prev.get("adjusted_close") or 0) - 1.0))
        except (TypeError, ValueError, ZeroDivisionError):
            continue
    med_ret = None
    if returns:
        ordered = sorted(returns)
        mid = len(ordered) // 2
        med_ret = ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2
        med_ret = round(med_ret, 2)

    sentiment = "Neutral"
    if avg_ret is not None:
        if avg_ret >= 0.35:
            sentiment = "Risk On"
        elif avg_ret <= -0.35:
            sentiment = "Risk Off"

    heatmap = current["heatmap"]
    ratio = advancing / max(1, advancing + declining)
    bullish_sessions = sum(item["heatmap"] in {"Bullish", "Strong Bullish"} for item in sessions)
    bearish_sessions = sum(item["heatmap"] in {"Bearish", "Strong Bearish"} for item in sessions)
    confirmation = {
        "sessions": len(sessions),
        "bullish_sessions": bullish_sessions,
        "bearish_sessions": bearish_sessions,
        "bullish_confirmed": len(sessions) >= 2 and bullish_sessions >= 2,
        "bearish_confirmed": len(sessions) >= 2 and bearish_sessions >= 2,
    }

    return {
        "ok": True,
        "date": latest,
        "prior_date": prior,
        "advancing": advancing,
        "declining": declining,
        "unchanged": unchanged,
        "average_return_pct": avg_ret,
        "median_return_pct": med_ret,
        "sentiment": sentiment,
        "heatmap": heatmap,
        "recent_sessions": sessions,
        "confirmation": confirmation,
        "sample_size": len(returns),
        "tracked_universe": len(returns),
        "universe_definition": (
            "Breadth uses symbols with consecutive daily closes in warehouse.daily_market_history "
            f"for {latest} vs {prior}. Moves beyond ±0.05% count as advancing/declining; "
            f"within ±0.05% count as unchanged. Sample capped at {sample_limit} symbols per session."
        ),
        "untracked_reasons": [
            "No consecutive price history in warehouse for the latest two sessions",
            "Illiquid or suspended names excluded from daily_market_history",
            "Recently listed symbols pending history accumulation",
            "Valuation universe exceeds price-history coverage",
        ],
        "coverage": {
            "history": len(returns),
            "confidence": "high" if len(returns) >= 500 else "moderate" if len(returns) >= 100 else "low",
            "source": "warehouse.daily_market_history",
        },
    }
