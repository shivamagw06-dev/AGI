"""Institutional flow (FII/DII) — read from warehouse only."""

from __future__ import annotations

from typing import Any, Optional


def institutional_flows(*, limit: int = 120) -> dict[str, Any]:
    from institutional_warehouse import store

    try:
        rows = store.all_rows("institutional_flow", limit=limit)
    except Exception:
        rows = []

    if not rows:
        return {
            "ok": True,
            "available": False,
            "note": "No FII/DII rows in warehouse yet. Run POST /v1/market-intelligence/flows/refresh.",
            "coverage": {"source": "warehouse.institutional_flow", "history": 0, "confidence": "none"},
        }

    rows = sorted(rows, key=lambda r: (str(r.get("date") or ""), str(r.get("segment") or "")))
    cash_rows = [r for r in rows if str(r.get("segment") or "") in {"NSE_EQ", "CASH", "NSE_EQ|CASH"}]
    headline_rows = cash_rows or rows
    # The newest row that carries a figure, not simply the newest row.
    #
    # A row with a date and no values is not a session. One reached the table
    # from an empty POST to the ingest route and, being the newest by date, it
    # took the headline slot and blanked FII and DII on the dashboard while
    # real readings sat one row below it.
    def _has_values(row: dict[str, Any]) -> bool:
        return _num(row.get("fii_net")) is not None or _num(row.get("dii_net")) is not None

    priced_rows = [r for r in headline_rows if _has_values(r)]
    latest = (priced_rows or headline_rows)[-1] if headline_rows else {}
    fii_net = _num(latest.get("fii_net"))
    dii_net = _num(latest.get("dii_net"))
    latest_values_available = fii_net is not None or dii_net is not None
    combined = None
    if latest_values_available:
        combined = round((fii_net or 0) + (dii_net or 0), 2)

    def trend(days: int) -> Optional[float]:
        if len(headline_rows) < days:
            return None
        window = headline_rows[-days:]
        return round(sum(_num(r.get("fii_net") or 0) + _num(r.get("dii_net") or 0) for r in window), 2)

    explanation = _explain_flows(headline_rows[-5:] if len(headline_rows) >= 5 else headline_rows)

    series = [
        {
            "date": r.get("date"),
            "fii_net": _num(r.get("fii_net")),
            "dii_net": _num(r.get("dii_net")),
            "combined": round((_num(r.get("fii_net")) or 0) + (_num(r.get("dii_net")) or 0), 2),
            "source": r.get("source"),
        }
        for r in headline_rows[-60:]
    ]

    latest_date = str(latest.get("date") or "")
    latest_segments = {
        str(r.get("segment")): r
        for r in rows
        if str(r.get("date") or "") == latest_date
    }

    return {
        "ok": True,
        "available": True,
        "latest_values_available": latest_values_available,
        "latest_date": latest.get("date"),
        "fii_net": fii_net,
        "dii_net": dii_net,
        "fii_net_buy": fii_net if fii_net is not None and fii_net >= 0 else None,
        "fii_net_sell": abs(fii_net) if fii_net is not None and fii_net < 0 else None,
        "dii_net_buy": dii_net if dii_net is not None and dii_net >= 0 else None,
        "dii_net_sell": abs(dii_net) if dii_net is not None and dii_net < 0 else None,
        "net_institutional_flow": combined,
        "trend_5d": trend(5),
        "trend_20d": trend(20),
        "trend_monthly": trend(min(22, len(rows))),
        "series": series,
        "segments": latest_segments,
        "explanation": explanation,
        "coverage": {
            "history": len(headline_rows),
            "segment_history": len(rows),
            "first": rows[0].get("date") if rows else None,
            "last": latest.get("date"),
            "confidence": "high" if len(rows) >= 20 else "moderate" if len(rows) >= 5 else "low",
            "source": latest.get("source") or "warehouse.institutional_flow",
        },
        "provenance": {
            "source": latest.get("source") or "upstox",
            "updated_at": latest.get("_meta", {}).get("updated_at") if isinstance(latest.get("_meta"), dict) else None,
        },
    }


def _num(value: Any) -> Optional[float]:
    try:
        if value is None or isinstance(value, bool):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _explain_flows(recent: list[dict[str, Any]]) -> str:
    if not recent:
        return "Institutional flow history is not yet available in the warehouse."
    fii_vals = [_num(r.get("fii_net")) for r in recent]
    dii_vals = [_num(r.get("dii_net")) for r in recent]
    fii_obs = [v for v in fii_vals if v is not None]
    dii_obs = [v for v in dii_vals if v is not None]
    parts = []
    if fii_obs:
        fii_streak = sum(1 for v in fii_obs if v > 0)
        if fii_streak >= 3:
            parts.append(
                f"Foreign institutional investors were net buyers on {fii_streak} "
                f"of the last {len(fii_obs)} sessions with FII data."
            )
        elif fii_streak == 0:
            parts.append(
                "Foreign institutions were net sellers across recent sessions with FII data."
            )
    if dii_obs:
        dii_streak = sum(1 for v in dii_obs if v > 0)
        if dii_streak >= 3:
            parts.append("Domestic institutions provided supportive flow on recent sessions.")
    if not parts:
        parts.append("Institutional flows are mixed — no sustained one-direction streak in recent data.")
    parts.append("This is flow context, not a recommendation.")
    return " ".join(parts)
