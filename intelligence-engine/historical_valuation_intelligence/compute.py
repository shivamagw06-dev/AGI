"""Observation writers — reconstruct from prices + statements, never vendor ratios.

Wraps warehouse ``valuation_history.reconstruct_company`` and adds incremental
daily append + statement-forward recalculation.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Optional

from historical_valuation_intelligence.models import ENGINE_CODE, VERSION


def reconstruct(
    symbol: str,
    *,
    cadence: str = "daily",
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit_observations: int = 8000,
    actor: str = "hvie",
) -> dict[str, Any]:
    """Full / ranged reconstruction into warehouse.historical_valuation."""
    from institutional_warehouse.backfill.valuation_history import reconstruct_company

    result = reconstruct_company(
        symbol,
        actor=actor,
        cadence=cadence,
        start=start,
        end=end,
        limit_observations=limit_observations,
    )
    return {
        **result,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "method": "point_in_time_reconstruction",
        "vendor_historical_ratios": False,
    }


def incremental_price_update(
    symbol: str,
    *,
    actor: str = "hvie",
) -> dict[str, Any]:
    """Append observations from the last warehouse cursor forward (daily)."""
    from institutional_warehouse.backfill import checkpoints

    ticker = str(symbol or "").strip().upper()
    cursor = None
    try:
        cp = checkpoints.load_checkpoint("valuation_history", ticker) or {}
        cursor = cp.get("cursor") or cp.get("last_period")
    except Exception:
        cursor = None

    start = None
    if cursor:
        try:
            start = (datetime.fromisoformat(str(cursor)[:10]).date() + timedelta(days=1)).isoformat()
        except Exception:
            start = str(cursor)

    return reconstruct(
        ticker,
        cadence="daily",
        start=start,
        limit_observations=400,
        actor=actor,
    )


def recalculate_from_statement(
    symbol: str,
    release_date: Optional[str] = None,
    *,
    actor: str = "hvie",
) -> dict[str, Any]:
    """Forward-only recalculation from statement release date."""
    start = release_date or (date.today() - timedelta(days=120)).isoformat()
    return reconstruct(
        symbol,
        cadence="daily",
        start=start,
        limit_observations=4000,
        actor=actor,
    )


def ensure_history(
    symbol: str,
    *,
    min_observations: int = 12,
    cadence: str = "monthly",
) -> dict[str, Any]:
    """If the warehouse is thin for a symbol, run a reconstruction."""
    from institutional_warehouse import store

    ticker = str(symbol or "").strip().upper()
    rows = store.all_rows("historical_valuation", entity=ticker, limit=50) or []
    if len(rows) >= min_observations:
        return {
            "ok": True,
            "symbol": ticker,
            "action": "skip",
            "observations": len(rows),
            "engine": ENGINE_CODE,
            "version": VERSION,
        }
    result = reconstruct(ticker, cadence=cadence, limit_observations=2000)
    return {**result, "action": "reconstruct"}
