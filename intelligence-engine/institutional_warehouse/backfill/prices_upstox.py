"""Daily price backfill from Upstox, replacing the monthly series Yahoo left.

Mirrors prices.py - same checkpointing, same screening, same gateway - but
pulls genuinely daily bars. See sources/upstox_history for why the Yahoo stage
produced a monthly series while reporting success for every company.

Corporate actions are deliberately not written here. Upstox candles arrive
already adjusted, so there is no ratio to record and nothing for
price_adjustment to corroborate; the existing corporate_actions rows stay as
they are.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Callable, Iterable, Optional

from institutional_warehouse import gateway, store
from institutional_warehouse.backfill import checkpoints
from institutional_warehouse.backfill.sources import upstox_history
from institutional_warehouse.backfill.validation import screen_series

KIND = "upstox_prices"
SOURCE = upstox_history.SOURCE
# A company whose history is mostly monthly has not been backfilled, whatever
# the checkpoint says. This is the check the Yahoo stage never applied.
MIN_DAILY_SHARE = 0.80


def _one_row_per_key(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse duplicate (symbol, date) rows, keeping the last.

    daily_market_history keys on (symbol, date) and the store splits a payload
    into inserts and updates before writing, with no ON CONFLICT clause. Two
    rows sharing a key therefore both land in the insert batch and the whole
    call fails with "UNIQUE constraint failed: wh_daily_market_history.row_id",
    losing every company in the run rather than the offending row.
    """
    deduped: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (str(row.get("symbol") or "").upper(), str(row.get("date") or "")[:10])
        deduped[key] = row
    return list(deduped.values())


def _companies() -> dict[str, str]:
    """{symbol: instrument_key} for every company we can address."""
    out: dict[str, str] = {}
    for row in store.all_rows("company_master", limit=20000) or []:
        symbol = str(row.get("symbol") or "").strip().upper()
        key = upstox_history.instrument_key(row)
        if symbol and key:
            out[symbol] = key
    return out


def backfill_company(
    symbol: str,
    *,
    instrument_key: Optional[str] = None,
    actor: str = "backfill",
    start: date = upstox_history.EARLIEST,
    end: Optional[date] = None,
    getter: Optional[Callable[[str], dict[str, Any]]] = None,
    pause_seconds: float = 0.0,
) -> dict[str, Any]:
    ticker = str(symbol).upper()
    key = instrument_key or _companies().get(ticker)
    if not key:
        checkpoints.save_checkpoint(KIND, ticker, status=checkpoints.FAILED,
                                    error="no_instrument_key")
        return {"ok": False, "symbol": ticker, "error": "no_instrument_key", "rows": 0}

    history = upstox_history.fetch_history(ticker, key, start=start, end=end,
                                           getter=getter, pause_seconds=pause_seconds)
    if not history.get("ok"):
        checkpoints.save_checkpoint(KIND, ticker, status=checkpoints.FAILED,
                                    error=str(history.get("error"))[:200])
        return {"ok": False, "symbol": ticker, "error": history.get("error"), "rows": 0}

    screened = screen_series(history["prices"], date_field="date")
    clean = _one_row_per_key(screened["accepted"])
    share = upstox_history.daily_share(clean)

    if share < MIN_DAILY_SHARE:
        # Refuse to record success for a series that is not daily. Marking this
        # done is exactly how the monthly data came to look like coverage.
        checkpoints.save_checkpoint(KIND, ticker, status=checkpoints.FAILED,
                                    error=f"not_daily:{share:.3f}")
        return {"ok": False, "symbol": ticker, "error": "series_is_not_daily",
                "daily_share": round(share, 4), "rows": 0}

    written = gateway.write("daily_market_history", clean, source=SOURCE, actor=actor,
                            reason=f"backfill:upstox:{ticker}")
    checkpoints.save_checkpoint(
        KIND, ticker, status=checkpoints.DONE, cursor=history.get("last"),
        rows_written=len(clean), first_period=history.get("first"),
        last_period=history.get("last"), reset_attempts=True,
    )
    return {
        "ok": True, "symbol": ticker, "rows": len(clean),
        "rejected": len(screened["rejected"]), "daily_share": round(share, 4),
        "first": history.get("first"), "last": history.get("last"),
        "window_errors": history.get("errors") or [], "written": written,
    }


def backfill(
    universe: Optional[Iterable[str]] = None,
    *,
    actor: str = "backfill",
    limit: int = 25,
    start: date = upstox_history.EARLIEST,
    end: Optional[date] = None,
    getter: Optional[Callable[[str], dict[str, Any]]] = None,
    pause_seconds: float = 0.0,
    refresh_done: bool = False,
) -> dict[str, Any]:
    keys = _companies()
    names = list(universe) if universe is not None else sorted(keys)
    pending = checkpoints.pending_entities(KIND, names, limit=limit, refresh_done=refresh_done)

    done: list[str] = []
    failed: list[dict[str, Any]] = []
    rows = 0
    earliest: Optional[str] = None

    for ticker in pending:
        try:
            result = backfill_company(ticker, instrument_key=keys.get(ticker.upper()), actor=actor,
                                      start=start, end=end, getter=getter,
                                      pause_seconds=pause_seconds)
        except Exception as exc:
            # One company must not take the batch down with it. A write that
            # raised previously aborted the whole stage, so 24 healthy
            # companies were lost to one bad payload.
            checkpoints.save_checkpoint(KIND, ticker, status=checkpoints.FAILED,
                                        error=str(exc)[:200])
            failed.append({"symbol": ticker, "error": str(exc)[:200]})
            continue
        if not result.get("ok"):
            failed.append({"symbol": ticker, "error": result.get("error"),
                           "daily_share": result.get("daily_share")})
            continue
        done.append(ticker)
        rows += int(result.get("rows") or 0)
        first = result.get("first")
        if first and (earliest is None or first < earliest):
            earliest = first

    return {
        "ok": True, "kind": KIND, "queued": len(pending),
        "companies_done": len(done), "companies_failed": len(failed),
        "rows_written": rows, "earliest_history": earliest,
        "addressable_companies": len(keys),
        "failures": failed[:20],
        "coverage": checkpoints.entity_coverage(KIND),
    }
