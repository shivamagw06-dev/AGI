"""Ingest market valuation metrics into the terminal store.

Source files are Yahoo Finance pulls keyed by NSE symbol. Every row is joined
to the canonical Company Identity so the terminal always knows which metrics
are meaningful for that company's industry.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from valuation_terminal import store

# Yahoo field → terminal field
_FIELD_MAP: dict[str, str] = {
    "currentPrice": "price",
    "marketCap": "market_cap",
    "trailingPE": "pe",
    "forwardPE": "forward_pe",
    "priceToBook": "pb",
    "enterpriseToEbitda": "ev_ebitda",
    "enterpriseToRevenue": "ev_sales",
    "priceToSalesTrailing12Months": "ps",
    "bookValue": "book_value",
    "trailingEps": "eps",
    "dividendYield": "dividend_yield",
    "debtToEquity": "debt_to_equity",
}

# Ratios Yahoo returns as fractions that read better as percentages.
_PERCENT_FIELDS = {"returnOnEquity": "roe", "profitMargins": "profit_margin"}


def _clean(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    # Yahoo occasionally returns absurd multiples for broken denominators.
    if out != out or abs(out) > 1e9:
        return None
    return out


def _sane(field: str, value: Optional[float]) -> Optional[float]:
    """Drop values that are arithmetically impossible or useless."""
    if value is None:
        return None
    if field in {"pe", "forward_pe", "ev_ebitda", "ev_sales", "ps", "pb"} and value <= 0:
        return None
    if field in {"pe", "forward_pe"} and value > 500:
        return None
    if field == "dividend_yield" and value > 40:
        return None
    return value


def _round(field: str, value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    if field in {"market_cap"}:
        return round(value)
    if field in {"price", "book_value", "eps"}:
        return round(value, 2)
    return round(value, 2)


def normalise_row(raw: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for src, dst in _FIELD_MAP.items():
        row[dst] = _round(dst, _sane(dst, _clean(raw.get(src))))
    for src, dst in _PERCENT_FIELDS.items():
        value = _clean(raw.get(src))
        row[dst] = round(value * 100.0, 2) if value is not None else None
    return row


def ingest_files(paths: list[str | Path], *, source: str = "yahoo_finance") -> dict[str, Any]:
    """Load one or more Yahoo pull files into the store."""
    from company_identity.service import identity_for

    merged: dict[str, dict[str, Any]] = {}
    read = 0
    for path in paths:
        p = Path(path)
        if not p.exists():
            continue
        try:
            payload = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        for raw in payload if isinstance(payload, list) else []:
            symbol = str(raw.get("symbol") or "").strip().upper()
            if not symbol or not raw.get("ok"):
                continue
            read += 1
            metrics = normalise_row(raw)
            if not any(v is not None for v in metrics.values()):
                continue
            identity = identity_for(symbol)
            merged[symbol] = {
                "ticker": symbol,
                "company_name": (
                    identity.company_name if identity.resolved else raw.get("name") or symbol
                ),
                "primary_sector": identity.primary_sector if identity.resolved else None,
                "primary_industry": identity.primary_industry if identity.resolved else None,
                "industry_dna": identity.industry_dna if identity.resolved else None,
                "business_type": identity.business_type if identity.resolved else None,
                "nse_industry": raw.get("industry"),
                "source": source,
                **metrics,
            }

    payload = store.save(merged, source=source)
    resolved = sum(1 for r in merged.values() if r.get("primary_sector"))
    return {
        "ok": True,
        "rows_read": read,
        "companies_stored": len(merged),
        "identity_resolved": resolved,
        "updated_at": payload.get("updated_at"),
        "source": source,
    }


def default_sources() -> list[Path]:
    """Committed pull files, newest first."""
    root = Path(__file__).resolve().parents[2] / "market_data"
    return sorted(root.glob("nse_valuation*.json")) + sorted(root.glob("nifty500_valuation*.json"))


def seed_if_needed(*, force: bool = False) -> dict[str, Any]:
    """Retired — terminal reads the warehouse via the Unified Valuation Engine."""
    return {
        "ok": False,
        "retired": True,
        "skipped": True,
        "reason": "json_loader_retired",
        "note": (
            "market_data/*valuation*.json ingest is retired. "
            "Use Warehouse → Unified Valuation Engine → Terminal."
        ),
        "force": bool(force),
    }
