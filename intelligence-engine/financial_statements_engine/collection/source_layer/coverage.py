"""Mission Control — Source Coverage dashboard (FSE-02.3)."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.collection.source_layer.metrics import coverage_summary
from financial_statements_engine.collection.source_layer.registry import registry_manifest, registry_rows
from financial_statements_engine.util import now_iso

WORKSTREAM_ID = "FSE-02.3"
VERSION = "fse-02.3-v1.0.0"
SPEC = "docs/FSE_02_3_OFFICIAL_SOURCE_REGISTRY.md"


def source_coverage_dashboard() -> dict[str, Any]:
    cov = coverage_summary()
    rows = registry_rows()
    download_success = None
    total_attempts = sum(int(r.get("attempts") or 0) for r in rows)
    total_success = sum(int(r.get("successes") or 0) for r in rows)
    if total_attempts:
        download_success = round(100.0 * total_success / total_attempts, 2)
    return {
        "status": "ok",
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "coverage_by_source": cov.get("coverage_by_source"),
        "coverage_by_company": cov.get("coverage_by_company"),
        "coverage_by_filing_type": cov.get("coverage_by_filing_type"),
        "coverage_by_reporting_year": cov.get("coverage_by_reporting_year"),
        "source_health": [
            {
                "source_id": r["source_id"],
                "source_name": r["source_name"],
                "priority": r["priority"],
                "status": r["status"],
                "health": r["health"],
                "success_rate_pct": r["success_rate_pct"],
                "average_download_time_ms": r["average_download_time_ms"],
                "supported_filing_types": r["supported_filing_types"],
            }
            for r in rows
        ],
        "download_success_pct": download_success,
        "average_latency_ms": cov.get("average_latency_ms"),
        "failures": cov.get("failures"),
        "fallback_usage": cov.get("fallback_usage"),
        "registry": registry_manifest(),
        "parses_financials": False,
        "writes_warehouse": False,
        "issues_recommendations": False,
        "spec": SPEC,
        "as_of": now_iso(),
    }


def source_registry_health() -> dict[str, Any]:
    return {
        "status": "ok",
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "registry": registry_manifest(),
        "changes_parser": False,
        "changes_vfqe": False,
        "changes_warehouse": False,
        "changes_dme": False,
        "changes_orchestrator": False,
        "spec": SPEC,
        "as_of": now_iso(),
    }
