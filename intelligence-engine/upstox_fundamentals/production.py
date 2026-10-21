"""UIFI production surface — health, coverage, warehouse reads."""

from __future__ import annotations

from typing import Any

from upstox_fundamentals.models import DATASETS, ENGINE_CODE, VERSION
from upstox_fundamentals.ingest import ingest_bundle


def health() -> dict[str, Any]:
    return {
        "ok": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "role": "primary_structured_fundamentals_provider",
        "source": "upstox",
        "secondary_corporate_actions": True,
        "datasets": list(DATASETS),
        "warehouse_tabs": [
            "company_master",
            "profile_history",
            "financials_annual",
            "financials_quarterly",
            "ownership",
            "peer_relationships",
            "corporate_actions",
            "valuation_ratios",
        ],
        "endpoints": [
            "/v1/upstox-fundamentals/health",
            "/v1/upstox-fundamentals/coverage",
            "/v1/upstox-fundamentals/failures",
            "/v1/upstox-fundamentals/ingest",
            "/v1/company/profile/{symbol}",
            "/v1/company/statements/{symbol}",
            "/v1/company/shareholding/{symbol}",
            "/v1/company/competitors/{symbol}",
            "/v1/company/corporate-actions/{symbol}",
            "/v1/company/profile/history/{symbol}",
        ],
        "rule": "products_read_warehouse_only",
    }


def _count(tab: str, *, source: str | None = None) -> int:
    from institutional_warehouse import store

    try:
        filters = {"source": source} if source else None
        return int(store.fetch(tab, filters=filters, limit=1).get("total") or 0)
    except Exception:
        try:
            rows = store.all_rows(tab, limit=50000)
            if source:
                rows = [r for r in rows if str(r.get("source") or "") == source]
            return len(rows)
        except Exception:
            return 0


def _distinct_symbols(tab: str, *, source: str | None = "upstox") -> int:
    from institutional_warehouse import store

    try:
        rows = store.all_rows(tab, limit=100000)
    except Exception:
        return 0
    syms = set()
    for r in rows:
        if source and str(r.get("source") or "") != source:
            # company_master may have been upserted with upstox source
            if tab == "company_master" and r.get("instrument_key"):
                pass
            elif source:
                continue
        sym = str(r.get("symbol") or "").upper()
        if sym:
            syms.add(sym)
    return len(syms)


def coverage() -> dict[str, Any]:
    from institutional_warehouse import store

    masters = []
    try:
        masters = store.all_rows("company_master", limit=100000)
    except Exception:
        masters = []
    total = len(masters)
    with_isin = sum(1 for r in masters if r.get("isin"))
    with_ikey = sum(1 for r in masters if r.get("instrument_key"))
    profiles = _count("profile_history", source="upstox")
    return {
        "ok": True,
        "engine": ENGINE_CODE,
        "companies": total,
        "with_isin": with_isin,
        "with_instrument_key": with_ikey,
        "isin_coverage_pct": round(100.0 * with_isin / total, 2) if total else 0.0,
        "profiles": profiles,
        "profile_symbols": _distinct_symbols("profile_history"),
        "statements_annual": _count("financials_annual", source="upstox"),
        "statements_quarterly": _count("financials_quarterly", source="upstox"),
        "ownership": _count("ownership", source="upstox"),
        "competitors": _count("peer_relationships", source="upstox"),
        "corporate_actions": _count("corporate_actions", source="upstox"),
        "valuation_ratios": _count("valuation_ratios", source="upstox"),
        "checked_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
    }


def failures() -> dict[str, Any]:
    """Surface recent quarantined / conflict rows related to Upstox when available."""
    from institutional_warehouse import store

    conflicts = []
    try:
        rows = store.all_rows("data_quality", limit=500)
        for r in rows:
            src = str(r.get("source") or r.get("feed") or "").lower()
            if "upstox" in src or str(r.get("provider") or "").lower() == "upstox":
                conflicts.append(r)
    except Exception:
        pass
    return {"ok": True, "count": len(conflicts), "rows": conflicts[:100]}


def _fetch_symbol(tab: str, symbol: str, *, limit: int = 200) -> list[dict[str, Any]]:
    from institutional_warehouse import store

    ticker = str(symbol).upper()
    try:
        return store.fetch(tab, filters={"symbol": ticker}, limit=limit).get("rows") or []
    except Exception:
        try:
            return [r for r in store.all_rows(tab, limit=5000)
                    if str(r.get("symbol") or "").upper() == ticker][:limit]
        except Exception:
            return []


def company_profile(symbol: str) -> dict[str, Any]:
    rows = _fetch_symbol("company_master", symbol, limit=1)
    return {"ok": bool(rows), "symbol": symbol.upper(), "profile": rows[0] if rows else None}


def company_profile_history(symbol: str) -> dict[str, Any]:
    rows = _fetch_symbol("profile_history", symbol, limit=100)
    return {"ok": True, "symbol": symbol.upper(), "history": rows, "count": len(rows)}


def company_statements(symbol: str) -> dict[str, Any]:
    annual = _fetch_symbol("financials_annual", symbol, limit=80)
    quarterly = _fetch_symbol("financials_quarterly", symbol, limit=120)
    return {
        "ok": True,
        "symbol": symbol.upper(),
        "annual": annual,
        "quarterly": quarterly,
        "count": len(annual) + len(quarterly),
    }


def company_shareholding(symbol: str) -> dict[str, Any]:
    rows = _fetch_symbol("ownership", symbol, limit=80)
    return {"ok": True, "symbol": symbol.upper(), "shareholding": rows, "count": len(rows)}


def company_competitors(symbol: str) -> dict[str, Any]:
    rows = _fetch_symbol("peer_relationships", symbol, limit=80)
    return {"ok": True, "symbol": symbol.upper(), "competitors": rows, "count": len(rows)}


def company_corporate_actions(symbol: str) -> dict[str, Any]:
    rows = _fetch_symbol("corporate_actions", symbol, limit=120)
    return {"ok": True, "symbol": symbol.upper(), "corporate_actions": rows, "count": len(rows)}
