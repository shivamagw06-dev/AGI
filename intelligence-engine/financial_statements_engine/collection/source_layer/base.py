"""Common adapter interface for official evidence sources (FSE-02.3).

Adapters discover and download only. They never call Parser / VFQE / Warehouse / DME.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SourceAdapter(Protocol):
    source_id: str
    display_name: str
    priority: int

    def discover(self, ticker: str, **kwargs: Any) -> list[dict[str, Any]]:
        """Return discovery rows (URLs + metadata). Never downloads bytes."""
        ...

    def download(self, discovery_row: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        """Download bytes for one discovery row. Never parses."""
        ...

    def metadata(self, discovery_row: dict[str, Any]) -> dict[str, Any]:
        """Normalize provenance metadata for a discovery row."""
        ...

    def health(self) -> dict[str, Any]:
        """Adapter health / readiness (no side effects on engines)."""
        ...


FILING_TYPES = (
    "annual_report",
    "quarterly_results",
    "xbrl",
    "financial_statements",
    "consolidated",
    "standalone",
)


def normalize_discovery(
    *,
    ticker: str,
    source_id: str,
    source_priority: int,
    document_type: str,
    period_type: str | None,
    period_end: str | None,
    source_url: str | None,
    filing_date: str | None = None,
    filing_type: str | None = None,
    company_name: str | None = None,
    consolidation: str | None = None,
    original_filename: str | None = None,
    mime_type: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row = {
        "ticker": ticker.upper().strip(),
        "company_id": f"nse:{ticker.upper().strip()}",
        "company_name": company_name,
        "source": source_id,
        "source_id": source_id,
        "source_priority": int(source_priority),
        "document_type": document_type,
        "period_type": period_type or "unknown",
        "period_end": period_end,
        "reporting_period": period_end,
        "filing_date": filing_date,
        "filing_type": filing_type or period_type or document_type,
        "source_url": source_url,
        "consolidation": consolidation,
        "original_filename": original_filename,
        "mime_type": mime_type,
    }
    if extra:
        row.update(extra)
    return row
