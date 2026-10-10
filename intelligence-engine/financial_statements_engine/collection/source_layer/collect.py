"""Multi-source collector → FSE-02 ingest() only (FSE-02.3).

Never calls Parser, VFQE, Warehouse, or DME.
"""

from __future__ import annotations

from typing import Any

from financial_statements_engine.collection.ingest import ingest
from financial_statements_engine.collection.source_layer.fallback import collect_with_fallback
from financial_statements_engine.collection.source_layer.provenance import (
    build_provenance,
    persist_provenance,
    record_duplicate_provenance,
)
from financial_statements_engine.raw_evidence import content_sha256
from financial_statements_engine.util import now_iso


def collect_and_ingest(
    ticker: str,
    *,
    filing_type: str | None = None,
    period_end: str | None = None,
    company_name: str | None = None,
    adapters: list[Any] | None = None,
) -> dict[str, Any]:
    """Fallback collect across official sources, then canonical ingest."""
    collected = collect_with_fallback(
        ticker,
        filing_type=filing_type,
        period_end=period_end,
        adapters=adapters,
    )
    if not collected.get("ok"):
        return {
            "ok": False,
            "ticker": ticker.upper().strip(),
            "error": collected.get("error") or "collection_failed",
            "attempts": collected.get("attempts") or [],
            "ingested": False,
            "as_of": now_iso(),
        }

    meta = collected.get("discovery") or {}
    raw = collected["bytes"]
    digest = content_sha256(raw)
    alts = []
    for d in collected.get("alternate_discoveries") or []:
        alts.append(
            {
                "source": d.get("source_id") or d.get("source"),
                "source_url": d.get("source_url"),
                "source_priority": d.get("source_priority"),
                "reporting_period": d.get("period_end") or d.get("reporting_period"),
                "filing_date": d.get("filing_date"),
            }
        )
    provenance = build_provenance(
        ticker=str(meta.get("ticker") or ticker),
        source_id=str(collected.get("source_id") or meta.get("source_id")),
        source_priority=int(collected.get("source_priority") or meta.get("source_priority") or 99),
        document_hash=digest,
        source_url=meta.get("source_url"),
        company_name=company_name or meta.get("company_name"),
        filing_type=meta.get("filing_type") or filing_type,
        reporting_period=meta.get("reporting_period") or meta.get("period_end") or period_end,
        filing_date=meta.get("filing_date"),
        original_filename=meta.get("original_filename"),
        mime_type=meta.get("mime_type"),
        company_id=meta.get("company_id"),
        alternate_sources=alts,
    )

    result = ingest(
        ticker=str(meta.get("ticker") or ticker),
        content=raw,
        source=str(collected.get("source_id") or meta.get("source_id")),
        document_type=str(meta.get("document_type") or "unknown"),
        period_type=meta.get("period_type"),
        period_end=meta.get("period_end") or period_end,
        source_url=meta.get("source_url"),
        company_name=provenance.get("company_name"),
        filing_type=provenance.get("filing_type"),
        collector="fse02_3_source_layer",
        provenance=provenance,
    )

    if result.get("action") == "duplicate_skipped":
        record_duplicate_provenance(
            document_hash=str(result.get("content_sha256") or digest),
            source_id=str(collected.get("source_id")),
            source_url=meta.get("source_url"),
            source_priority=int(collected.get("source_priority") or 99),
            reporting_period=provenance.get("reporting_period"),
            filing_date=provenance.get("filing_date"),
        )
    else:
        persist_provenance(str(result.get("content_sha256") or digest), provenance)

    return {
        "ok": bool(result.get("ok")),
        "ticker": ticker.upper().strip(),
        "source_id": collected.get("source_id"),
        "fallback_used": collected.get("fallback_used"),
        "attempts": collected.get("attempts"),
        "ingest": {
            "action": result.get("action"),
            "evidence_id": result.get("evidence_id"),
            "event_emitted": result.get("event_emitted"),
            "content_sha256": result.get("content_sha256"),
        },
        "provenance": provenance,
        "ingested": result.get("action") in {"stored", "restatement_candidate", "duplicate_skipped"},
        "as_of": now_iso(),
    }
