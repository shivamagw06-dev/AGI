"""Ingest hooks — fire HVIE forward/CA rebuilds after warehouse writes.

Called from refresh stages so quarterly results and corporate actions
immediately maintain historical_valuation without waiting for the weekly job.
Failures are swallowed and logged; ingest must never fail because of HVIE.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Iterable, Optional

log = logging.getLogger("hvie.hooks")


def _symbols(rows: Iterable[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for row in rows or []:
        sym = str(row.get("symbol") or row.get("ticker") or "").strip().upper()
        if sym and sym not in seen:
            seen.add(sym)
            out.append(sym)
    return out


def after_statements_written(
    rows: list[dict[str, Any]] | None = None,
    *,
    symbols: Optional[list[str]] = None,
    as_of: Optional[str | date] = None,
) -> dict[str, Any]:
    """Forward-rebuild from statement release date → today for affected names."""
    tickers = list(symbols or []) or _symbols(rows or [])
    if not tickers:
        return {"ok": True, "triggered": 0}
    try:
        from historical_valuation_intelligence.runtime import forward_rebuild_company
    except Exception as exc:
        log.warning("hvie forward hook unavailable: %s", exc)
        return {"ok": False, "error": str(exc)[:200]}

    results = []
    for sym in tickers[:80]:
        try:
            release = as_of.isoformat() if hasattr(as_of, "isoformat") else as_of
            results.append(forward_rebuild_company(sym, release_date=release))
        except Exception as exc:
            log.warning("hvie forward rebuild %s failed: %s", sym, exc)
            results.append({"symbol": sym, "ok": False, "error": str(exc)[:160]})
    return {"ok": True, "triggered": len(results), "results": results}


def after_corporate_actions_written(
    rows: list[dict[str, Any]] | None = None,
    *,
    symbols: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Full historical reconstruct for names with split/bonus/rights/etc."""
    tickers = list(symbols or []) or _symbols(rows or [])
    # Only structural CAs force a full rebuild.
    structural = {"split", "bonus", "rights", "buyback", "merger", "demerger"}
    if rows and not symbols:
        tickers = []
        seen: set[str] = set()
        for row in rows:
            kind = str(row.get("action_type") or "").strip().lower()
            if kind and kind not in structural:
                continue
            sym = str(row.get("symbol") or row.get("ticker") or "").strip().upper()
            if sym and sym not in seen:
                seen.add(sym)
                tickers.append(sym)
    if not tickers:
        return {"ok": True, "triggered": 0}
    try:
        from historical_valuation_intelligence.runtime import corporate_action_rebuild
    except Exception as exc:
        log.warning("hvie CA hook unavailable: %s", exc)
        return {"ok": False, "error": str(exc)[:200]}

    results = []
    for sym in tickers[:40]:
        try:
            results.append(corporate_action_rebuild(sym))
        except Exception as exc:
            log.warning("hvie CA rebuild %s failed: %s", sym, exc)
            results.append({"symbol": sym, "ok": False, "error": str(exc)[:160]})
    return {"ok": True, "triggered": len(results), "results": results}
