"""Long-term recommendation outcome stubs — calibrated forward returns.

Does not invent prices. When a price history series is available, compute
simple forward returns; otherwise mark horizons as pending.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def long_term_performance_stub(
    row: dict[str, Any],
    *,
    as_of: str | None = None,
    horizons: tuple[str, ...] = ("30d", "90d", "180d", "365d"),
) -> dict[str, Any]:
    """Attach outcome placeholders for future calibration jobs."""
    ticker = str(row.get("ticker") or "").upper()
    returns: dict[str, Any] = {}
    series_found = False
    try:
        from institutional_reasoning.fundamentals.market_series import monthly_returns

        series = monthly_returns(ticker)
        series_found = bool(series)
    except Exception:
        series = None

    for h in horizons:
        returns[h] = {
            "status": "pending_calibration" if not series_found else "series_available_not_aligned",
            "return_pct": None,
            "note": (
                "Forward return alignment runs in a separate calibration job; "
                "golden evaluation records the recommendation context only."
            ),
        }

    return {
        "ticker": ticker,
        "recommendation_date": as_of or _now(),
        "decision": row.get("decision"),
        "recommendation_readiness": row.get("recommendation_readiness"),
        "live_price_at_decision": row.get("price_ltp"),
        "horizons": returns,
        "max_drawdown_pct": None,
        "price_history_available": series_found,
        "objective": (
            "Measure whether recommendations are directionally sound and calibrated — "
            "not maximise returns on every call."
        ),
    }


def attach_performance_stubs(rows: list[dict[str, Any]], *, as_of: str | None = None) -> list[dict[str, Any]]:
    out = []
    for r in rows:
        item = dict(r)
        item["performance"] = long_term_performance_stub(r, as_of=as_of)
        out.append(item)
    return out
