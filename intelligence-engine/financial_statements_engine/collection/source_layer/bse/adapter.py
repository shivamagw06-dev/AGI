"""BSE Official Filing adapter — wraps existing FSE-02 BSE discovery (FSE-02.3)."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.collection.adapters.bse import discover_bse
from financial_statements_engine.collection.downloader import download_bytes
from financial_statements_engine.collection.source_layer import config as cfg
from financial_statements_engine.collection.source_layer.base import normalize_discovery
from financial_statements_engine.util import now_iso


class BseSourceAdapter:
    source_id = "bse_official"
    display_name = "BSE Official Filing"
    priority = 3

    def __init__(self, *, injected_rows: list[dict[str, Any]] | None = None, injected_bytes: dict[str, bytes] | None = None):
        self._injected_rows = injected_rows
        self._injected_bytes = injected_bytes or {}

    def discover(self, ticker: str, **kwargs: Any) -> list[dict[str, Any]]:
        t = ticker.upper().strip()
        if self._injected_rows is not None:
            return [self._norm(t, r) for r in self._injected_rows]
        raw = discover_bse(t, **kwargs)
        return [self._norm(t, r) for r in raw]

    def _norm(self, ticker: str, item: dict[str, Any]) -> dict[str, Any]:
        doc = str(item.get("document_type") or "pdf")
        return normalize_discovery(
            ticker=ticker,
            source_id=self.source_id,
            source_priority=self.priority,
            document_type=doc,
            period_type=item.get("period_type"),
            period_end=item.get("period_end"),
            source_url=item.get("source_url") or item.get("url"),
            filing_date=item.get("filing_date"),
            filing_type=item.get("filing_type") or item.get("period_type") or doc,
            company_name=item.get("company_name"),
            consolidation=item.get("consolidation"),
            original_filename=item.get("original_filename"),
            mime_type=item.get("mime_type") or ("application/pdf" if doc == "pdf" else "application/octet-stream"),
        )

    def metadata(self, discovery_row: dict[str, Any]) -> dict[str, Any]:
        return self._norm(str(discovery_row.get("ticker") or ""), discovery_row)

    def download(self, discovery_row: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        url = discovery_row.get("source_url") or discovery_row.get("url")
        if url and str(url) in self._injected_bytes:
            return download_bytes(str(url), data=self._injected_bytes[str(url)])
        pe = str(discovery_row.get("period_end") or "")
        if pe and pe in self._injected_bytes:
            return download_bytes(pe, data=self._injected_bytes[pe])
        return download_bytes(str(url) if url else None, timeout_s=cfg.source_timeout_s())

    def health(self) -> dict[str, Any]:
        enabled = cfg.enable_bse()
        return {
            "status": "ok" if enabled else "disabled",
            "source_id": self.source_id,
            "enabled": enabled,
            "wraps": "collection.adapters.bse.discover_bse",
            "priority": self.priority,
            "as_of": now_iso(),
        }
