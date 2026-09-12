"""Eligibility engine — classify every company before HVIE bootstrap."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from historical_valuation_intelligence.universe_programme.models import (
    LIFE_NOT_STARTED,
    LIFE_READY,
    LIFE_WAITING_PRICE,
    LIFE_WAITING_SHARE_COUNT,
    LIFE_WAITING_STATEMENTS,
    MIN_PRICE_OBS,
    MIN_STATEMENT_OBS,
    STAGE_CLASSIFY,
)
from historical_valuation_intelligence.universe_programme.queue import upsert_queue_row


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _entity_has(tab_id: str, symbol: str, *, min_rows: int = 1) -> tuple[bool, int, Optional[str], Optional[str]]:
    """Return (ok, count, first, last) for an entity tab."""
    from institutional_warehouse import store

    ticker = str(symbol or "").strip().upper()
    try:
        page = store.fetch(tab_id, entity=ticker, sort="date", order="asc", limit=max(min_rows, 5))
        rows = page.get("rows") or []
        total = int(page.get("total") or len(rows))
    except Exception:
        try:
            rows = store.all_rows(tab_id, entity=ticker, limit=max(min_rows, 20)) or []
            total = len(rows)
        except Exception:
            return False, 0, None, None
    if not rows:
        return False, 0, None, None
    first = str(rows[0].get("date") or rows[0].get("fiscal_year") or rows[0].get("as_of") or "")[:10] or None
    last = str(rows[-1].get("date") or rows[-1].get("fiscal_year") or rows[-1].get("as_of") or "")[:10] or None
    # Prefer total when available
    return total >= min_rows, total, first, last


def _statements_available(symbol: str) -> tuple[bool, int]:
    ok_a, n_a, _, _ = _entity_has("financials_annual", symbol, min_rows=MIN_STATEMENT_OBS)
    ok_q, n_q, _, _ = _entity_has("financials_quarterly", symbol, min_rows=MIN_STATEMENT_OBS)
    total = n_a + n_q
    return (ok_a or ok_q), total


def _has_share_count(symbol: str) -> tuple[bool, Optional[float]]:
    """Share count from FWCP share_count_history, statements, or prices — required for P/B and EV."""
    ticker = str(symbol or "").strip().upper()
    # Phase 7.4F — prefer dedicated share_count_history tab.
    try:
        from financial_warehouse_completion.share_count import has_share_count as fwcp_shares

        ok, shares = fwcp_shares(ticker)
        if ok:
            return True, shares
    except Exception:
        pass
    from institutional_warehouse import store
    from institutional_warehouse.values import to_number

    for tab in ("share_count_history", "financials_annual", "financials_quarterly", "daily_market_history"):
        try:
            rows = store.fetch(tab, entity=ticker, limit=20).get("rows") or []
        except Exception:
            rows = []
        for row in rows:
            shares = to_number(
                row.get("shares_outstanding") or row.get("diluted_shares") or row.get("weighted_average_shares")
            )
            if shares is not None and shares > 0:
                return True, shares
    return False, None


def _policy(symbol: str) -> tuple[Optional[str], Optional[str]]:
    try:
        from valuation_policy import evaluate

        pack = evaluate(symbol) or {}
        if pack.get("ok"):
            return (
                str(pack.get("primary_metric") or "pe"),
                str(pack.get("primary_model") or "") or None,
            )
    except Exception:
        pass
    return "pe", None


def classify_company(symbol: str, *, master: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Determine eligibility and blocking reason; persist onto the queue row."""
    ticker = str(symbol or "").strip().upper()
    has_price, price_n, first, last = _entity_has(
        "daily_market_history", ticker, min_rows=MIN_PRICE_OBS,
    )
    has_stmt, stmt_n = _statements_available(ticker)
    # Corporate actions are optional for eligibility (empty is fine).
    has_ca, ca_n, _, _ = _entity_has("corporate_actions", ticker, min_rows=0)
    # Presence check without requiring rows:
    try:
        from institutional_warehouse import store

        ca_page = store.fetch("corporate_actions", entity=ticker, limit=1)
        ca_n = int(ca_page.get("total") or 0)
        has_ca = True  # table reachable; zero rows is OK
    except Exception:
        has_ca = True
        ca_n = 0

    primary_metric, primary_model = _policy(ticker)

    lifecycle = LIFE_READY
    eligible = True
    blocking = None
    reason = "ready_for_hvie"

    has_shares, share_n = _has_share_count(ticker)

    if not has_price:
        lifecycle = LIFE_WAITING_PRICE
        eligible = False
        blocking = "missing_price_history"
        reason = f"Need ≥{MIN_PRICE_OBS} daily_market_history rows; found {price_n}."
    elif not has_stmt:
        lifecycle = LIFE_WAITING_STATEMENTS
        eligible = False
        blocking = "missing_statements"
        reason = f"Need annual or quarterly statements; found {stmt_n}."
    elif not has_shares:
        lifecycle = LIFE_WAITING_SHARE_COUNT
        eligible = False
        blocking = "missing_share_count"
        reason = "Need shares_outstanding on statements or daily_market_history for P/B and EV."

    row = upsert_queue_row(
        ticker,
        lifecycle=lifecycle if eligible or lifecycle != LIFE_NOT_STARTED else LIFE_NOT_STARTED,
        stage=STAGE_CLASSIFY,
        eligible=eligible,
        blocking_reason=blocking,
        reason=reason,
        history_window_first=first,
        history_window_last=last,
        primary_metric=primary_metric,
        primary_model=primary_model,
        sector=(master or {}).get("sector"),
        industry=(master or {}).get("industry") or (master or {}).get("industry_dna"),
        classified_at=_now(),
        # Preserve queue_status unless brand new — caller manages transitions.
    )
    # If waiting on inputs, park as SKIPPED? Spec: WAITING_* lifecycle with pending until ready.
    # Keep PENDING so reclassify can promote when data arrives.
    return {
        "ok": True,
        "symbol": ticker,
        "eligible": eligible,
        "lifecycle": lifecycle,
        "blocking_reason": blocking,
        "reason": reason,
        "price_observations": price_n,
        "statement_observations": stmt_n,
        "has_share_count": has_shares,
        "shares_outstanding": share_n,
        "corporate_actions": ca_n,
        "has_corporate_actions_table": has_ca,
        "primary_metric": primary_metric,
        "primary_model": primary_model,
        "history_window": {"first": first, "last": last},
        "row": row,
    }
