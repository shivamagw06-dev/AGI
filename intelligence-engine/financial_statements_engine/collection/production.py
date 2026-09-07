"""FSE-02 / FSE-02.1 collection subsystem — production façades."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.collection.adapters.nse import discover_nse
from financial_statements_engine.collection.event_bus import get_bus
from financial_statements_engine.collection.flags import canonical_ingest_enabled, dual_write_hd_enabled
from financial_statements_engine.collection.ingest import MIGRATION_VERSION
from financial_statements_engine.collection.ingest_metrics import summarize_ingest_metrics
from financial_statements_engine.collection.pipeline import collect_from_discovery_rows
from financial_statements_engine.collection.schema import (
    ISSUES_RECOMMENDATIONS,
    PROGRAMME,
    RECOMMENDATION_POLICY,
    SUBSYSTEM,
    SUCCESS_TARGETS,
    VERSION,
    WORKSTREAM_ID,
)
from financial_statements_engine.collection.sources import sources_manifest
from financial_statements_engine.schema import GOLD_UNIVERSE
from financial_statements_engine.util import now_iso


def health() -> dict[str, Any]:
    bus = get_bus().stats()
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "workstream_id": WORKSTREAM_ID,
        "subsystem": SUBSYSTEM,
        "version": VERSION,
        "migration": MIGRATION_VERSION,
        "role": "data_sources_collection_pipeline",
        "canonical_ingest": canonical_ingest_enabled(),
        "dual_write_hd": dual_write_hd_enabled(),
        "event_bus": bus,
        "sources": sources_manifest(),
        "success_targets": SUCCESS_TARGETS,
        "issues_recommendations": ISSUES_RECOMMENDATIONS,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "parses_financials": False,
        "writes_warehouse": False,
        "spec": "docs/FSE_02_DATA_SOURCES_COLLECTION_PIPELINE.md",
        "migration_spec": "docs/FSE_02_1_CANONICAL_INGESTION_MIGRATION.md",
        "as_of": now_iso(),
    }


def dashboard() -> dict[str, Any]:
    bus = get_bus().stats()
    return {
        "status": "ok",
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "migration": MIGRATION_VERSION,
        "event_bus": bus,
        "recent_events": get_bus().tail(20),
        "ingest": summarize_ingest_metrics(),
        "success_targets": SUCCESS_TARGETS,
        "issues_recommendations": False,
        "as_of": now_iso(),
    }


def source_coverage() -> dict[str, Any]:
    """FSE-02.3 Mission Control — official source coverage dashboard."""
    from financial_statements_engine.collection.source_layer.coverage import source_coverage_dashboard

    return source_coverage_dashboard()


def source_registry() -> dict[str, Any]:
    from financial_statements_engine.collection.source_layer.coverage import source_registry_health

    return source_registry_health()


def collect_official(ticker: str, **kwargs: Any) -> dict[str, Any]:
    """Multi-source official collect → FSE-02 ingest (FSE-02.3)."""
    from financial_statements_engine.collection.source_layer.collect import collect_and_ingest

    return collect_and_ingest(ticker, **kwargs)


def ingest_dashboard() -> dict[str, Any]:
    """FSE-02.1 Mission Control — canonical ingestion dashboard."""
    metrics = summarize_ingest_metrics()
    bus = get_bus().stats()
    stored_events = int((bus.get("by_type") or {}).get("evidence.stored") or 0)
    dup_events = int((bus.get("by_type") or {}).get("evidence.duplicate_skipped") or 0)
    return {
        "status": "ok",
        "workstream_id": "FSE-02.1",
        "migration": MIGRATION_VERSION,
        "canonical_ingest": canonical_ingest_enabled(),
        "dual_write_hd": dual_write_hd_enabled(),
        "collected_today": metrics.get("collected_today"),
        "duplicate_filings": metrics.get("duplicate_filings"),
        "failed_downloads": metrics.get("failed_downloads"),
        "stored_evidence": metrics.get("stored_evidence"),
        "event_emissions": metrics.get("event_emissions"),
        "average_ingest_latency_ms": metrics.get("average_ingest_latency_ms"),
        "source_distribution": metrics.get("source_distribution"),
        "latest_filing_time": metrics.get("latest_filing_time"),
        "bus_evidence_stored": stored_events,
        "bus_duplicate_skipped": dup_events,
        "recent_events": get_bus().tail(20),
        "issues_recommendations": False,
        "spec": "docs/FSE_02_1_CANONICAL_INGESTION_MIGRATION.md",
        "as_of": now_iso(),
    }


def collect_ticker(
    ticker: str,
    *,
    mode: str = "live",
    rows: list[dict[str, Any]] | None = None,
    bytes_by_url: dict[str, bytes] | None = None,
) -> dict[str, Any]:
    t = ticker.upper().strip()
    discovery_rows = rows if rows is not None else discover_nse(t)
    result = collect_from_discovery_rows(t, discovery_rows, mode=mode, bytes_by_url=bytes_by_url)
    result.update(
        {
            "engine": "financial_statements_engine",
            "workstream_id": WORKSTREAM_ID,
            "version": VERSION,
            "recommendation_policy": RECOMMENDATION_POLICY,
            "issues_recommendations": False,
            "as_of": now_iso(),
        }
    )
    return result


def run_universe(universe: str = "gold", *, mode: str = "live") -> dict[str, Any]:
    tickers = list(GOLD_UNIVERSE) if universe in ("gold", "ic5") else list(GOLD_UNIVERSE)
    rows = [collect_ticker(t, mode=mode) for t in tickers]
    return {
        "ok": True,
        "workstream_id": WORKSTREAM_ID,
        "universe": universe,
        "mode": mode,
        "n": len(rows),
        "rows": rows,
        "issues_recommendations": False,
        "as_of": now_iso(),
    }


def recent_events(limit: int = 50) -> dict[str, Any]:
    return {
        "ok": True,
        "workstream_id": WORKSTREAM_ID,
        "events": get_bus().tail(limit),
        "issues_recommendations": False,
        "as_of": now_iso(),
    }
