"""Upstox-first statement fill for EMPTY / thin equities (INE* ISIN).

Yahoo fundamentals are often blocked on cloud egress. Upstox
`/v2/fundamentals/{isin}/income-statement|balance-sheet|cash-flow` works
from production with the existing Bearer token. Fetch happens on the Node
BFF; this module owns the EMPTY+INE queue and status surface.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from financial_warehouse_completion.models import ENGINE_CODE, PROGRAMME_CODE, PROGRAMME_VERSION
from financial_warehouse_completion.yahoo_fill import _looks_non_equity, clear_queue_cache


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def queue_candidates(
    *,
    limit: int = 200,
    include_thin: bool = True,
    exclude: Optional[list[str] | set[str] | tuple[str, ...]] = None,
) -> dict[str, Any]:
    """EMPTY → MINIMAL → thin, requiring INE* equity ISIN (skip INF* funds)."""
    from financial_warehouse_completion.audit import (
        CLASS_EMPTY,
        CLASS_MINIMAL,
        CLASS_PARTIAL,
        _annual_stats,
        _classify,
        _index_by_symbol,
        _load_rows,
        _quarterly_stats,
        clear_audit_cache,
    )

    # Queue must see freshly written statement rows (not a stale audit scan).
    clear_audit_cache()
    clear_queue_cache()

    exclude_set = {
        str(s or "").strip().upper()
        for s in (exclude or [])
        if str(s or "").strip()
    }

    masters = _load_rows("company_master", limit=100000)
    annual_ix = _index_by_symbol(_load_rows("financials_annual", limit=500000))
    quarterly_ix = _index_by_symbol(_load_rows("financials_quarterly", limit=500000))

    empty: list[dict[str, Any]] = []
    minimal: list[dict[str, Any]] = []
    thin: list[dict[str, Any]] = []
    skipped_no_isin = 0
    skipped_non_equity = 0
    skipped_excluded = 0

    for m in masters:
        sym = str(m.get("symbol") or "").strip().upper()
        if not sym:
            continue
        if sym in exclude_set:
            skipped_excluded += 1
            continue
        isin = str(m.get("isin") or "").strip().upper()
        if _looks_non_equity(sym, m.get("company_name"), isin):
            skipped_non_equity += 1
            continue
        if not isin.startswith("INE"):
            skipped_no_isin += 1
            continue
        a = _annual_stats(annual_ix.get(sym) or [])
        q = _quarterly_stats(quarterly_ix.get(sym) or [])
        years = int(a["years"])
        quarters = int(q["quarters"])
        klass = _classify(years, quarters)
        row = {
            "symbol": sym,
            "company_name": m.get("company_name"),
            "sector": m.get("sector") or "Unknown",
            "isin": isin,
            "instrument_key": m.get("instrument_key") or f"NSE_EQ|{isin}",
            "classification": klass,
            "annual_years": years,
            "quarters": quarters,
            "priority": 1 if klass == CLASS_EMPTY else 2 if klass == CLASS_MINIMAL else 3,
        }
        if klass == CLASS_EMPTY:
            empty.append(row)
        elif klass == CLASS_MINIMAL:
            minimal.append(row)
        elif include_thin and (years < 4 or quarters < 5 or (klass == CLASS_PARTIAL and years < 4)):
            thin.append(row)

    ranked = empty + minimal + thin
    ranked.sort(key=lambda r: (r["priority"], r["annual_years"], r["quarters"], r["symbol"]))
    cap = max(1, min(int(limit), 5000))
    return {
        "ok": True,
        "programme": PROGRAMME_CODE,
        "engine": ENGINE_CODE,
        "version": PROGRAMME_VERSION,
        "source": "upstox",
        "provider_api": "/v2/fundamentals/{isin}/income-statement|balance-sheet|cash-flow",
        "units_in": "crore",
        "counts": {
            "empty": len(empty),
            "minimal": len(minimal),
            "thin": len(thin),
            "queued": min(len(ranked), cap),
            "total_candidates": len(ranked),
            "skipped_non_equity": skipped_non_equity,
            "skipped_no_ine_isin": skipped_no_isin,
            "skipped_excluded": skipped_excluded,
            "universe": len(masters),
        },
        "rows": ranked[:cap],
        "plain_english": (
            f"Upstox queue: {len(empty)} EMPTY, {len(minimal)} MINIMAL, {len(thin)} thin "
            f"with INE* ISIN. Skipped {skipped_non_equity} funds/ETFs and {skipped_no_isin} "
            f"without INE ISIN. Node BFF fetches Upstox → UIFI ingest → warehouse."
        ),
        "checked_at": _now(),
    }


def board() -> dict[str, Any]:
    q = queue_candidates(limit=25, include_thin=True)
    return {
        "ok": True,
        "programme": PROGRAMME_CODE,
        "engine": ENGINE_CODE,
        "version": PROGRAMME_VERSION,
        "source": "upstox",
        "queue_preview": q,
        "progress": q.get("counts"),
        "plain_english": q.get("plain_english"),
        "what_this_does": (
            "Fills EMPTY/thin equity statements from Upstox fundamentals by ISIN "
            "(income-statement, balance-sheet, cash-flow — yearly + quarterly, consolidated). "
            "Crore → INR million via warehouse units. Prefer this over Yahoo on Render."
        ),
        "admin_actions": {
            "start": "POST /api/upstox/statements/fill-empty",
            "run": "POST /api/upstox/refresh {dataset:statements, symbols:[...]}",
            "queue": "GET /v1/warehouse/upstox-fill/queue",
        },
        "checked_at": _now(),
    }


def mark_queue_dirty() -> None:
    clear_queue_cache()
