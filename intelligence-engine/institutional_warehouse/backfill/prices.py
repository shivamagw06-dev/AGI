"""Price and corporate-action backfill from Yahoo into the warehouse tabs.

Writes raw observations only: OHLCV, adjusted close, volume, dividends and
splits exactly as the source reported them. Market cap, ratios and multiples are
the formula engine's job, not this module's.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable, Optional

from institutional_warehouse import gateway, store
from institutional_warehouse.backfill import checkpoints
from institutional_warehouse.backfill.sources import yahoo_history
from institutional_warehouse.backfill.validation import screen_series

KIND = "yahoo_prices"
SOURCE = yahoo_history.SOURCE


def backfill_company(
    symbol: str,
    *,
    actor: str = "backfill",
    fetch: Optional[Callable[[str], bytes]] = None,
    range_: str = "max",
    pause_seconds: float = 0.0,
) -> dict[str, Any]:
    """Full available price history for one company, plus its dividends and splits."""
    ticker = str(symbol).upper()
    history = yahoo_history.fetch_history(ticker, range_=range_, fetch=fetch,
                                          pause_seconds=pause_seconds)
    if not history.get("ok"):
        checkpoints.save_checkpoint(KIND, ticker, status=checkpoints.FAILED,
                                    error=str(history.get("error"))[:200])
        return {"ok": False, "symbol": ticker, "error": history.get("error"), "rows": 0}

    rows = [{**row, "symbol": ticker, "source": SOURCE} for row in history["prices"]]
    screened = screen_series(rows, date_field="date")
    clean = screened["accepted"]

    written = gateway.write("daily_market_history", clean, source=SOURCE, actor=actor,
                           reason=f"backfill:yahoo:{ticker}")

    actions = _action_rows(ticker, history)
    action_result = gateway.write("corporate_actions", actions, source=SOURCE, actor=actor,
                                 reason=f"backfill:yahoo_actions:{ticker}") if actions else {}

    checkpoints.save_checkpoint(
        KIND,
        ticker,
        status=checkpoints.DONE,
        cursor=history.get("last"),
        rows_written=len(clean),
        first_period=history.get("first"),
        last_period=history.get("last"),
        reset_attempts=True,
    )
    return {
        "ok": True,
        "symbol": ticker,
        "rows": len(clean),
        "rejected": len(screened["rejected"]),
        "warnings": len(screened["warnings"]),
        "first": history.get("first"),
        "last": history.get("last"),
        "years": _years(history.get("first"), history.get("last")),
        "written": written,
        "actions": action_result,
    }


def _action_rows(ticker: str, history: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for dividend in history.get("dividends") or []:
        if not dividend.get("date"):
            continue
        rows.append(
            {
                "symbol": ticker,
                "action_date": dividend["date"],
                "action_type": "dividend",
                "dividend": dividend.get("amount"),
                "details": f"dividend {dividend.get('amount')}",
                "source": SOURCE,
            }
        )
    for split in history.get("splits") or []:
        if not split.get("date"):
            continue
        ratio = split.get("ratio")
        if not ratio and split.get("numerator") and split.get("denominator"):
            ratio = f"{split['numerator']}:{split['denominator']}"
        rows.append(
            {
                "symbol": ticker,
                "action_date": split["date"],
                "action_type": "split",
                "split": ratio,
                "details": f"split {ratio}",
                "source": SOURCE,
            }
        )
    return rows


def _years(first: Optional[str], last: Optional[str]) -> Optional[float]:
    if not first or not last:
        return None
    try:
        from datetime import date

        a = date.fromisoformat(first)
        b = date.fromisoformat(last)
        return round((b - a).days / 365.25, 2)
    except Exception:
        return None


def backfill(
    universe: Optional[Iterable[str]] = None,
    *,
    actor: str = "backfill",
    limit: int = 25,
    fetch: Optional[Callable[[str], bytes]] = None,
    range_: str = "max",
    pause_seconds: float = 0.0,
    refresh_done: bool = False,
) -> dict[str, Any]:
    """Walk the pending companies and pull each one's full history."""
    names = list(universe) if universe is not None else store.entities("company_master")
    pending = checkpoints.pending_entities(KIND, names, limit=limit, refresh_done=refresh_done)

    done: list[str] = []
    failed: list[dict[str, Any]] = []
    rows = 0
    deepest = {"symbol": None, "years": 0.0}

    for ticker in pending:
        result = backfill_company(ticker, actor=actor, fetch=fetch, range_=range_,
                                  pause_seconds=pause_seconds)
        if not result.get("ok"):
            failed.append({"symbol": ticker, "error": result.get("error")})
            continue
        done.append(ticker)
        rows += int(result.get("rows") or 0)
        years = float(result.get("years") or 0.0)
        if years > deepest["years"]:
            deepest = {"symbol": ticker, "years": years}

    return {
        "ok": True,
        "kind": KIND,
        "queued": len(pending),
        "companies_done": len(done),
        "companies_failed": len(failed),
        "rows_written": rows,
        "deepest": deepest,
        "failures": failed[:20],
        "coverage": checkpoints.entity_coverage(KIND),
    }
