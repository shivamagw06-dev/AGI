"""Metadata Collector — filing metadata only, no accounting line items (FSE-02 §6.3)."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.util import now_iso


def extract_filing_metadata(discovery_row: dict[str, Any]) -> dict[str, Any]:
    """Normalize discovery/index fields into collection metadata."""
    return {
        "ticker": str(discovery_row.get("ticker") or discovery_row.get("symbol") or "").upper().strip() or None,
        "entity": discovery_row.get("entity"),
        "source": discovery_row.get("source"),
        "source_url": discovery_row.get("source_url") or discovery_row.get("url") or discovery_row.get("xbrl"),
        "document_type": (discovery_row.get("document_type") or discovery_row.get("doc_type") or "unknown"),
        "period_type": discovery_row.get("period_type") or "unknown",
        "period_end": discovery_row.get("period_end") or discovery_row.get("end_date"),
        "fiscal_year": discovery_row.get("fiscal_year"),
        "fiscal_period": discovery_row.get("fiscal_period") or discovery_row.get("period"),
        "filing_date": discovery_row.get("filing_date") or discovery_row.get("filed_at"),
        "exchange_ref": discovery_row.get("exchange_ref") or discovery_row.get("attachment_id"),
        "document_id": discovery_row.get("document_id") or discovery_row.get("id"),
        "taxonomy_version": discovery_row.get("taxonomy_version"),
        "consolidation": discovery_row.get("consolidation"),
        "collected_meta_at": now_iso(),
        "layer": "metadata_collector",
        # Explicitly exclude any line-item payloads if present
        "interprets_financials": False,
    }
