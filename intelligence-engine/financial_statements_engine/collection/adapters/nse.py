"""NSE discovery adapter — wraps P2.1 earnings_intelligence discovery when available."""

from __future__ import annotations

from typing import Any


def discover_nse(ticker: str, **kwargs: Any) -> list[dict[str, Any]]:
    """Return discovery rows for NSE filings (URLs + metadata only)."""
    t = ticker.upper().strip()
    try:
        from earnings_intelligence import discovery as ei_discovery  # type: ignore
    except Exception:
        ei_discovery = None

    rows: list[dict[str, Any]] = []
    if ei_discovery is not None:
        for fn_name in ("discover_filings", "list_filings", "discover", "integrated_filing_index"):
            fn = getattr(ei_discovery, fn_name, None)
            if callable(fn):
                try:
                    raw = fn(t, **kwargs)
                except TypeError:
                    try:
                        raw = fn(t)
                    except Exception:
                        continue
                except Exception:
                    continue
                if isinstance(raw, dict):
                    raw = raw.get("filings") or raw.get("rows") or raw.get("items") or []
                if isinstance(raw, list):
                    for item in raw:
                        if not isinstance(item, dict):
                            continue
                        rows.append(_normalize_nse_row(t, item))
                    if rows:
                        break
    return rows


def _normalize_nse_row(ticker: str, item: dict[str, Any]) -> dict[str, Any]:
    return {
        "ticker": ticker,
        "source": item.get("source")
        or (
            "nse_xbrl"
            if str(item.get("document_type") or item.get("doc_type") or "").lower() == "xbrl"
            or item.get("xbrl")
            else "nse_integrated_filing"
        ),
        "document_type": item.get("document_type") or ("xbrl" if item.get("xbrl") else item.get("doc_type") or "html"),
        "period_type": item.get("period_type") or item.get("result_type") or "unknown",
        "period_end": item.get("period_end") or item.get("end_date") or item.get("to_date"),
        "fiscal_year": item.get("fiscal_year"),
        "fiscal_period": item.get("fiscal_period") or item.get("period"),
        "filing_date": item.get("filing_date") or item.get("filed_at") or item.get("date"),
        "source_url": item.get("source_url") or item.get("url") or item.get("xbrl") or item.get("attchmntFile"),
        "exchange_ref": item.get("exchange_ref") or item.get("attachment_id"),
        "taxonomy_version": item.get("taxonomy_version"),
        "consolidation": item.get("consolidation"),
    }
