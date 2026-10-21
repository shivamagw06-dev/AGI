"""BSE discovery adapter — placeholder soft-delegate (FSE-02)."""

from __future__ import annotations

from typing import Any


def discover_bse(ticker: str, **kwargs: Any) -> list[dict[str, Any]]:
    """Return BSE discovery rows when a connector is available; else empty."""
    t = ticker.upper().strip()
    try:
        # Soft optional — do not fail collection package import
        from institutional_data.connectors import bse as bse_mod  # type: ignore
    except Exception:
        return []

    rows: list[dict[str, Any]] = []
    for fn_name in ("discover_financial_filings", "list_filings", "discover"):
        fn = getattr(bse_mod, fn_name, None)
        if not callable(fn):
            continue
        try:
            raw = fn(t, **kwargs)
        except Exception:
            continue
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    rows.append(
                        {
                            "ticker": t,
                            "source": "bse_filing",
                            "document_type": item.get("document_type") or "pdf",
                            "period_type": item.get("period_type") or "unknown",
                            "period_end": item.get("period_end"),
                            "source_url": item.get("source_url") or item.get("url"),
                            "filing_date": item.get("filing_date"),
                        }
                    )
            break
    return rows
