"""Financial statement backfill.

Raw statement lines only — revenue, EBITDA, PAT, equity, debt, cash flows and
the share count. Ratios and multiples are computed later by the formula engine
from whatever the warehouse holds, so nothing derived is stored here.

Yahoo carries roughly four annual years and four to six quarters. That is the
honest ceiling of this source; Capital IQ and filing-derived history append
alongside it later without overwriting, because every row is keyed by period
and carries its own source.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable, Optional

from institutional_warehouse import gateway, store
from institutional_warehouse.backfill import checkpoints
from institutional_warehouse.backfill.sources import yahoo_history

KIND = "yahoo_statements"
SOURCE = "yahoo_finance_statements"

_RAW_FIELDS = (
    "revenue", "gross_profit", "ebitda", "ebit", "pbt", "pat", "eps", "assets", "equity",
    "debt", "cash", "current_assets", "current_liabilities", "inventory", "working_capital",
    "capex", "cfo", "cfi", "cff", "free_cash_flow", "shares_outstanding",
)


def _rows(symbol: str, periods: Iterable[dict[str, Any]], *, quarterly: bool) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for period in periods:
        label = str(period.get("fiscal_label") or "").strip()
        if not label:
            continue
        row: dict[str, Any] = {"symbol": symbol, "source": SOURCE, "statement_version": "yahoo"}
        if quarterly:
            row["fiscal_period"] = label
            row["fiscal_year"] = label[:4] if label.startswith("FY") else None
            row["quarter"] = label[-2:] if label[-2:].startswith("Q") else None
        else:
            row["fiscal_year"] = label
        for field in _RAW_FIELDS:
            if period.get(field) is not None:
                row[field] = period[field]
        if any(row.get(f) is not None for f in ("revenue", "pat", "ebitda", "equity", "assets")):
            out.append(row)
    return out


def backfill_company(
    symbol: str,
    *,
    actor: str = "backfill",
    loader: Optional[Callable[[str], dict[str, Any]]] = None,
) -> dict[str, Any]:
    ticker = str(symbol).upper()
    payload = yahoo_history.fetch_statements(ticker, loader=loader)
    if not payload.get("ok"):
        checkpoints.save_checkpoint(KIND, ticker, status=checkpoints.FAILED,
                                    error=str(payload.get("error"))[:200])
        return {"ok": False, "symbol": ticker, "error": payload.get("error")}

    annual = _rows(ticker, payload.get("annual") or [], quarterly=False)
    quarterly = _rows(ticker, payload.get("quarterly") or [], quarterly=True)

    annual_result = gateway.write("financials_annual", annual, source=SOURCE, actor=actor,
                                 reason=f"backfill:statements:{ticker}") if annual else {}
    quarterly_result = gateway.write("financials_quarterly", quarterly, source=SOURCE, actor=actor,
                                    reason=f"backfill:statements:{ticker}") if quarterly else {}

    written = len(annual) + len(quarterly)
    checkpoints.save_checkpoint(
        KIND,
        ticker,
        status=checkpoints.DONE if written else checkpoints.SKIPPED,
        rows_written=written,
        first_period=(annual or quarterly or [{}])[0].get("fiscal_year")
        or (quarterly or [{}])[0].get("fiscal_period"),
        last_period=(annual or quarterly or [{}])[-1].get("fiscal_year")
        or (quarterly or [{}])[-1].get("fiscal_period"),
        reset_attempts=True,
    )
    return {
        "ok": True,
        "symbol": ticker,
        "annual_periods": len(annual),
        "quarterly_periods": len(quarterly),
        "annual": annual_result,
        "quarterly": quarterly_result,
    }


def backfill(
    universe: Optional[Iterable[str]] = None,
    *,
    actor: str = "backfill",
    limit: int = 25,
    loader: Optional[Callable[[str], dict[str, Any]]] = None,
    refresh_done: bool = False,
) -> dict[str, Any]:
    names = list(universe) if universe is not None else store.entities("company_master")
    pending = checkpoints.pending_entities(KIND, names, limit=limit, refresh_done=refresh_done)

    done: list[str] = []
    failed: list[dict[str, Any]] = []
    annual = quarterly = 0
    for ticker in pending:
        result = backfill_company(ticker, actor=actor, loader=loader)
        if not result.get("ok"):
            failed.append({"symbol": ticker, "error": result.get("error")})
            continue
        done.append(ticker)
        annual += int(result.get("annual_periods") or 0)
        quarterly += int(result.get("quarterly_periods") or 0)

    return {
        "ok": True,
        "kind": KIND,
        "queued": len(pending),
        "companies_done": len(done),
        "companies_failed": len(failed),
        "annual_periods": annual,
        "quarterly_periods": quarterly,
        "failures": failed[:20],
        "coverage": checkpoints.entity_coverage(KIND),
    }
