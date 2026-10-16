"""Global search across every sheet.

Searching "Axis Bank" returns the Company Master row, its statements, its
valuation snapshots, consensus, research, ownership and corporate actions —
one query, every tab.
"""

from __future__ import annotations

from typing import Any, Optional

from institutional_warehouse import db, store
from institutional_warehouse.schema import TABS, tab as get_tab
from institutional_warehouse.values import normalise_entity


def _resolve_entities(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Map free text ("Axis Bank") to warehouse symbols."""
    text = (query or "").strip()
    if not text:
        return []
    table = db.physical_table("company_master")
    like = f"%{text.lower()}%"
    rows = db.query(
        f'SELECT symbol, company_name, sector, industry FROM {table}'
        " WHERE LOWER(CAST(symbol AS TEXT)) = ? OR LOWER(CAST(company_name AS TEXT)) LIKE ?"
        " OR LOWER(CAST(legal_name AS TEXT)) LIKE ? OR LOWER(CAST(isin AS TEXT)) = ?"
        " ORDER BY CASE WHEN LOWER(CAST(symbol AS TEXT)) = ? THEN 0 ELSE 1 END, symbol LIMIT ?",
        (text.lower(), like, like, text.lower(), text.lower(), max(1, int(limit))),
    )
    return [
        {
            "symbol": r.get("symbol"),
            "company_name": r.get("company_name"),
            "sector": r.get("sector"),
            "industry": r.get("industry"),
        }
        for r in rows
    ]


def search(
    query: str,
    *,
    tabs: Optional[list[str]] = None,
    per_tab: int = 5,
    include_rows: bool = True,
) -> dict[str, Any]:
    text = (query or "").strip()
    if not text:
        return {"ok": False, "error": "empty_query"}

    matches = _resolve_entities(text)
    symbol = matches[0]["symbol"] if matches else None
    wanted = [t for t in TABS if not tabs or t.id in set(tabs)]

    results: list[dict[str, Any]] = []
    total = 0
    for tab in wanted:
        hits: list[dict[str, Any]] = []
        found = 0
        if symbol and tab.entity_column:
            page = store.fetch(tab.id, entity=symbol, limit=per_tab)
            hits, found = page["rows"], page["total"]
        if not hits:
            page = store.fetch(tab.id, search=text, limit=per_tab)
            hits, found = page["rows"], page["total"]
        if not found:
            continue
        total += found
        results.append(
            {
                "tab": tab.id,
                "label": tab.label,
                "matches": found,
                "rows": hits if include_rows else [],
            }
        )

    return {
        "ok": True,
        "query": text,
        "resolved": matches,
        "symbol": symbol,
        "total_matches": total,
        "tabs": results,
    }


def company_view(symbol: str, *, per_tab: int = 25) -> dict[str, Any]:
    """Everything the warehouse knows about one company, tab by tab."""
    ticker = normalise_entity(symbol)
    if not ticker:
        return {"ok": False, "error": "empty_symbol"}
    master = store.fetch("company_master", entity=ticker, limit=1)
    sheets: dict[str, Any] = {}
    for tab in TABS:
        if not tab.entity_column or tab.id == "company_master":
            continue
        page = store.fetch(tab.id, entity=ticker, limit=per_tab)
        sheets[tab.id] = {
            "label": tab.label,
            "total": page["total"],
            "rows": page["rows"],
        }
    return {
        "ok": True,
        "symbol": ticker,
        "master": (master["rows"] or [None])[0],
        "sheets": sheets,
        "coverage": {k: v["total"] for k, v in sheets.items()},
    }


def suggest(prefix: str, limit: int = 10) -> dict[str, Any]:
    text = (prefix or "").strip().lower()
    if not text:
        return {"ok": True, "suggestions": []}
    table = db.physical_table("company_master")
    rows = db.query(
        f"SELECT symbol, company_name FROM {table}"
        " WHERE LOWER(CAST(symbol AS TEXT)) LIKE ? OR LOWER(CAST(company_name AS TEXT)) LIKE ?"
        " ORDER BY symbol LIMIT ?",
        (f"{text}%", f"%{text}%", max(1, min(int(limit), 50))),
    )
    return {"ok": True, "suggestions": [{"symbol": r.get("symbol"), "name": r.get("company_name")} for r in rows]}
