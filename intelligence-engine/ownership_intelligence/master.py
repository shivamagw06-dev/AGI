"""NSE Shareholding Master — quarter timeline (correct field mapping)."""

from __future__ import annotations

import json
from typing import Any
from urllib.request import Request

from ownership_intelligence.dates import fiscal_quarter_label, parse_nse_date


NSE_MASTER_URL = (
    "https://www.nseindia.com/api/corporate-share-holdings-master?index=equities&symbol={symbol}"
)


def _f(v: Any) -> float | None:
    if v is None or v == "" or v == "-":
        return None
    try:
        return round(float(v), 4)
    except (TypeError, ValueError):
        return None


def fetch_nse_master(symbol: str, *, opener=None) -> list[dict[str, Any]]:
    """Fetch raw NSE shareholding master rows for a symbol."""
    from live_data.collectors.base import nse_session_opener

    key = (symbol or "").upper()
    if not key:
        return []
    op = opener or nse_session_opener()
    url = NSE_MASTER_URL.format(symbol=key)
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; AGIB-LIDI/1.0)",
            "Accept": "application/json",
            "Referer": f"https://www.nseindia.com/get-quotes/equity?symbol={key}",
        },
    )
    with op.open(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    if isinstance(data, dict):
        rows = data.get("data") or data.get("shareholding") or []
        return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []
    return []


def normalize_master_row(row: dict[str, Any], *, entity: str) -> dict[str, Any]:
    """Map NSE master fields correctly — never silently drop unknowns."""
    period_raw = row.get("date") or row.get("period") or row.get("asOnDate") or ""
    period_end = parse_nse_date(period_raw)
    filing = parse_nse_date(row.get("submissionDate") or row.get("broadcastDate"))
    out = {
        "entity": entity.upper(),
        "period_raw": str(period_raw),
        "period_end": period_end,
        "quarter_label": fiscal_quarter_label(period_end),
        "filing_date": filing,
        # Correct NSE Master mappings
        "promoter": _f(row.get("pr_and_prgrp")),
        "public": _f(row.get("public_val")),
        "employee_trusts": _f(row.get("employeeTrusts")),
        "isin": row.get("isin"),
        "name": row.get("name"),
        "record_id": row.get("recordId"),
        "xbrl_url": row.get("xbrl"),
        "xbrl_file_size": row.get("xbrlFileSize"),
        "broadcast_date": row.get("broadcastDate"),
        "submission_date": row.get("submissionDate"),
        "remarks": row.get("remarksWeb") if row.get("remarksWeb") not in (None, "N") else None,
        "source": "nse_master",
        "raw": dict(row),
    }
    return out


def quarter_timeline(symbol: str, *, opener=None, injected: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Build ordered quarter timeline from NSE master (newest first)."""
    key = (symbol or "").upper()
    if injected is not None:
        rows = [normalize_master_row(r, entity=key) for r in injected]
        mode = "injected"
    else:
        raw = fetch_nse_master(key, opener=opener)
        rows = [normalize_master_row(r, entity=key) for r in raw]
        mode = "live"
    # newest first (NSE usually already newest-first)
    rows.sort(key=lambda r: r.get("period_end") or "", reverse=True)
    return {
        "ok": bool(rows),
        "entity": key,
        "mode": mode,
        "quarters": rows,
        "count": len(rows),
        "latest": rows[0] if rows else None,
        "error": None if rows else "nse_master_empty",
    }
