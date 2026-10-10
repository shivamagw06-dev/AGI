"""Exposure aggregations from weighted holdings — no intelligence recalculation."""

from __future__ import annotations

from typing import Any, Mapping


def _bucket(holdings: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    acc: dict[str, float] = {}
    for h in holdings:
        key = str(h.get(field) or "Unknown")
        w = float(h.get("weight") or 0.0)
        acc[key] = acc.get(key, 0.0) + w
    rows = [{"name": k, "weight": v} for k, v in acc.items()]
    rows.sort(key=lambda r: r["weight"], reverse=True)
    return rows


def compute_exposures(portfolio: Mapping[str, Any]) -> dict[str, Any]:
    holdings = [dict(h) for h in (portfolio.get("holdings") or [])]
    cash = portfolio.get("cash") or {}
    currency_rows = _bucket(holdings, "currency") if any(h.get("currency") for h in holdings) else []
    # Include cash currency
    cash_ccy = str(cash.get("currency") or (portfolio.get("metadata") or {}).get("base_currency") or "INR")
    cash_w = float(cash.get("weight") or 0.0)
    ccy_map = {r["name"]: r["weight"] for r in currency_rows if r.get("name")}
    if cash_w:
        # If holdings lack currency, attribute equity to base and cash separately
        if not ccy_map:
            base = str((portfolio.get("metadata") or {}).get("base_currency") or cash_ccy)
            equity_w = sum(float(h.get("weight") or 0.0) for h in holdings)
            ccy_map[base] = ccy_map.get(base, 0.0) + equity_w
        ccy_map[cash_ccy] = ccy_map.get(cash_ccy, 0.0) + cash_w
    currency_rows = [{"name": k, "weight": v} for k, v in ccy_map.items()]
    currency_rows.sort(key=lambda r: r["weight"], reverse=True)

    return {
        "schema": "po01.exposures.v1",
        "sector": _bucket(holdings, "sector"),
        "industry": _bucket(holdings, "industry"),
        "country": _bucket(holdings, "country"),
        "market_cap": _bucket(holdings, "market_cap_bucket"),
        "currency": currency_rows,
        "note": "Weights from stated market values; PO-01 does not invent prices.",
    }
