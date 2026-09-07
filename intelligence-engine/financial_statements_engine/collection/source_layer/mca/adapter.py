"""MCA XBRL adapter — highest priority official source (FSE-02.3).

Soft-delegates to an optional MCA connector when present. Supports injected
discovery/download for tests and offline runs. Never parses.
"""

from __future__ import annotations

from typing import Any

from financial_statements_engine.collection.downloader import download_bytes
from financial_statements_engine.collection.source_layer import config as cfg
from financial_statements_engine.collection.source_layer.base import normalize_discovery
from financial_statements_engine.util import now_iso


class McaSourceAdapter:
    source_id = "mca_xbrl"
    display_name = "MCA XBRL"
    priority = 1

    def __init__(self, *, injected_rows: list[dict[str, Any]] | None = None, injected_bytes: dict[str, bytes] | None = None):
        self._injected_rows = injected_rows
        self._injected_bytes = injected_bytes or {}

    def discover(self, ticker: str, **kwargs: Any) -> list[dict[str, Any]]:
        t = ticker.upper().strip()
        if self._injected_rows is not None:
            return [self.metadata(r) if r.get("source_id") else self._norm(t, r) for r in self._injected_rows]

        rows: list[dict[str, Any]] = []
        try:
            from institutional_data.connectors import mca as mca_mod  # type: ignore
        except Exception:
            mca_mod = None
        if mca_mod is not None:
            for fn_name in ("discover_xbrl_filings", "discover_financial_filings", "discover", "list_filings"):
                fn = getattr(mca_mod, fn_name, None)
                if not callable(fn):
                    continue
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
                        if isinstance(item, dict):
                            rows.append(self._norm(t, item))
                    if rows:
                        break
        return rows

    def _norm(self, ticker: str, item: dict[str, Any]) -> dict[str, Any]:
        return normalize_discovery(
            ticker=ticker,
            source_id=self.source_id,
            source_priority=self.priority,
            document_type=str(item.get("document_type") or "xbrl"),
            period_type=item.get("period_type") or item.get("filing_type") or "annual",
            period_end=item.get("period_end") or item.get("reporting_period"),
            source_url=item.get("source_url") or item.get("url"),
            filing_date=item.get("filing_date"),
            filing_type=item.get("filing_type") or item.get("period_type") or "annual_report",
            company_name=item.get("company_name"),
            consolidation=item.get("consolidation"),
            original_filename=item.get("original_filename") or item.get("filename"),
            mime_type=item.get("mime_type") or "application/xml",
            extra={"exchange_ref": item.get("exchange_ref") or item.get("cin")},
        )

    def metadata(self, discovery_row: dict[str, Any]) -> dict[str, Any]:
        t = str(discovery_row.get("ticker") or "").upper()
        return self._norm(t, discovery_row)

    def download(self, discovery_row: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        url = discovery_row.get("source_url") or discovery_row.get("url")
        if url and url in self._injected_bytes:
            return download_bytes(str(url), data=self._injected_bytes[str(url)])
        # allow period_end key injection
        pe = str(discovery_row.get("period_end") or "")
        if pe and pe in self._injected_bytes:
            return download_bytes(pe, data=self._injected_bytes[pe])
        return download_bytes(str(url) if url else None, timeout_s=cfg.source_timeout_s())

    def health(self) -> dict[str, Any]:
        enabled = cfg.enable_mca()
        connector = False
        try:
            from institutional_data.connectors import mca as _mca  # noqa: F401

            connector = True
        except Exception:
            connector = False
        status = "ok" if enabled else "disabled"
        if enabled and not connector and self._injected_rows is None:
            status = "degraded"  # ready for injection / future connector
        return {
            "status": status,
            "source_id": self.source_id,
            "enabled": enabled,
            "connector_present": connector,
            "priority": self.priority,
            "as_of": now_iso(),
        }
