"""Derive and persist share_count_history from statements / price history."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from financial_warehouse_completion.dqiv_rules import validate_share_count_row
from financial_warehouse_completion.models import ENGINE_CODE, PROGRAMME_VERSION


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_of_from_statement(row: dict[str, Any], *, quarterly: bool) -> Optional[str]:
    for key in ("filing_date", "as_of", "period_end", "date"):
        val = row.get(key)
        if val:
            return str(val)[:10]
    if quarterly:
        return str(row.get("fiscal_period") or "")[:10] or None
    fy = str(row.get("fiscal_year") or "").strip().upper()
    if fy.startswith("FY") and len(fy) >= 4:
        try:
            year = 2000 + int(fy[2:4])
            return f"{year}-03-31"
        except ValueError:
            return None
    return None


def harvest_from_statements(symbol: str) -> list[dict[str, Any]]:
    """Build share-count rows from annual/quarterly statements."""
    from institutional_warehouse import store
    from institutional_warehouse.values import to_number

    ticker = str(symbol or "").strip().upper()
    out: list[dict[str, Any]] = []
    for tab, quarterly in (("financials_annual", False), ("financials_quarterly", True)):
        try:
            rows = store.fetch(tab, entity=ticker, limit=200).get("rows") or []
        except Exception:
            rows = store.all_rows(tab, entity=ticker, limit=200) or []
        for row in rows:
            shares = to_number(row.get("shares_outstanding"))
            basic = to_number(row.get("basic_shares") or row.get("shares_basic"))
            diluted = to_number(row.get("diluted_shares") or row.get("shares_diluted"))
            weighted = to_number(
                row.get("weighted_average_shares") or row.get("weighted_avg_shares")
            )
            if not any(v is not None and v > 0 for v in (shares, basic, diluted, weighted)):
                continue
            as_of = _as_of_from_statement(row, quarterly=quarterly)
            if not as_of:
                continue
            candidate = {
                "symbol": ticker,
                "as_of": as_of,
                "basic_shares": basic,
                "diluted_shares": diluted,
                "weighted_average_shares": weighted,
                "shares_outstanding": shares or diluted or weighted or basic,
                "statement_type": row.get("statement_type") or "UNKNOWN",
                "fiscal_period": row.get("fiscal_period") or row.get("fiscal_year"),
                "source": f"fwcp_from_{tab}",
            }
            gate = validate_share_count_row(candidate)
            if not gate.get("ok"):
                continue
            candidate["shares_outstanding"] = gate.get("canonical_shares")
            candidate["confidence"] = gate.get("confidence")
            candidate["dqiv_status"] = gate.get("status")
            candidate["validation_notes"] = "; ".join(gate.get("notes") or [])
            out.append(candidate)
    return out


def harvest_from_prices(symbol: str) -> list[dict[str, Any]]:
    """Fallback: last known shares_outstanding on daily_market_history."""
    from institutional_warehouse import store
    from institutional_warehouse.values import to_number

    ticker = str(symbol or "").strip().upper()
    try:
        rows = store.fetch("daily_market_history", entity=ticker, sort="date", order="desc", limit=60).get("rows") or []
    except Exception:
        rows = []
    out: list[dict[str, Any]] = []
    for row in rows:
        shares = to_number(row.get("shares_outstanding"))
        if shares is None or shares <= 0:
            continue
        candidate = {
            "symbol": ticker,
            "as_of": str(row.get("date") or "")[:10],
            "shares_outstanding": shares,
            "basic_shares": shares,
            "source": "fwcp_from_daily_market_history",
        }
        gate = validate_share_count_row(candidate)
        if not gate.get("ok"):
            continue
        candidate["confidence"] = min(0.55, float(gate.get("confidence") or 0.5))
        candidate["dqiv_status"] = gate.get("status")
        candidate["validation_notes"] = "derived_from_price_history"
        out.append(candidate)
        break  # latest only from prices
    return out


def sync_symbol(symbol: str, *, actor: str = "fwcp") -> dict[str, Any]:
    """Write harvested share counts for one symbol."""
    from institutional_warehouse import gateway

    ticker = str(symbol or "").strip().upper()
    rows = harvest_from_statements(ticker)
    if not rows:
        rows = harvest_from_prices(ticker)
    if not rows:
        return {
            "ok": False,
            "symbol": ticker,
            "written": 0,
            "error": "no_share_count_source",
            "engine": ENGINE_CODE,
            "version": PROGRAMME_VERSION,
        }
    # Deduplicate by (as_of, source)
    seen: set[tuple[str, str]] = set()
    clean: list[dict[str, Any]] = []
    for row in rows:
        key = (str(row.get("as_of")), str(row.get("source")))
        if key in seen:
            continue
        seen.add(key)
        clean.append(row)
    written = gateway.write(
        "share_count_history",
        clean,
        source="fwcp_share_count",
        actor=actor,
        reason="fwcp_share_count_sync",
    )
    return {
        "ok": bool(written.get("ok")),
        "symbol": ticker,
        "candidates": len(clean),
        "written": written.get("written") or written.get("inserted") or 0,
        "gateway": written,
        "engine": ENGINE_CODE,
        "version": PROGRAMME_VERSION,
        "checked_at": _now(),
    }


def has_share_count(symbol: str) -> tuple[bool, Optional[float]]:
    """Prefer dedicated share_count_history, then statements / prices."""
    from institutional_warehouse import store
    from institutional_warehouse.values import to_number

    ticker = str(symbol or "").strip().upper()
    try:
        page = store.fetch("share_count_history", entity=ticker, sort="as_of", order="desc", limit=5)
        for row in page.get("rows") or []:
            shares = to_number(row.get("shares_outstanding") or row.get("diluted_shares"))
            if shares is not None and shares > 0:
                return True, shares
    except Exception:
        pass
    # Fallbacks already used by HVIE
    for tab in ("financials_annual", "financials_quarterly", "daily_market_history"):
        try:
            rows = store.fetch(tab, entity=ticker, limit=20).get("rows") or []
        except Exception:
            rows = []
        for row in rows:
            shares = to_number(row.get("shares_outstanding"))
            if shares is not None and shares > 0:
                return True, shares
    return False, None
