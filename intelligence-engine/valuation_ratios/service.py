"""Health / coverage for Upstox valuation ratios."""

from __future__ import annotations

from typing import Any


def health() -> dict[str, Any]:
    from institutional_warehouse import db, store

    try:
        count = db.count(db.physical_table("valuation_ratios"))
    except Exception:
        count = 0
    sample = store.all_rows("valuation_ratios", limit=5) if count else []
    symbols = {str(r.get("symbol") or "") for r in sample if r.get("symbol")}
    return {
        "ok": True,
        "engine": "valuation_ratios",
        "version": "2.0",
        "provider": "upstox",
        "endpoint": "/fundamentals/{isin}/key-ratios",
        "rows": count,
        "sample_symbols": sorted(symbols)[:5],
        "data_path": "upstox → dqiv → warehouse.valuation_ratios → unified_valuation_engine",
    }


def coverage() -> dict[str, Any]:
    from institutional_warehouse import db, store

    try:
        total = db.count(db.physical_table("valuation_ratios"))
    except Exception:
        total = 0
    rows = store.all_rows("valuation_ratios", limit=20_000) if total else []
    by_ratio: dict[str, int] = {}
    symbols: set[str] = set()
    for row in rows:
        name = str(row.get("ratio_name") or "")
        by_ratio[name] = by_ratio.get(name, 0) + 1
        if row.get("symbol"):
            symbols.add(str(row["symbol"]).upper())
    return {
        "ok": True,
        "rows": total,
        "companies": len(symbols),
        "by_ratio": by_ratio,
        "source": "upstox",
    }
