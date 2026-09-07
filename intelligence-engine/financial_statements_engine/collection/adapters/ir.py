"""Company IR discovery adapter — lower priority than exchange XBRL (FSE-02)."""

from __future__ import annotations

from typing import Any


def discover_ir(ticker: str, **kwargs: Any) -> list[dict[str, Any]]:
    t = ticker.upper().strip()
    try:
        from institutional_data.connectors import ir_discovery  # type: ignore
    except Exception:
        return []

    fn = getattr(ir_discovery, "discover_ir_documents", None) or getattr(ir_discovery, "discover", None)
    if not callable(fn):
        return []
    try:
        raw = fn(t, **kwargs)
    except Exception:
        return []
    rows: list[dict[str, Any]] = []
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            rows.append(
                {
                    "ticker": t,
                    "source": "company_ir",
                    "document_type": item.get("document_type") or "pdf",
                    "period_type": item.get("period_type") or "unknown",
                    "period_end": item.get("period_end"),
                    "source_url": item.get("source_url") or item.get("url"),
                    "filing_date": item.get("filing_date"),
                }
            )
    return rows
