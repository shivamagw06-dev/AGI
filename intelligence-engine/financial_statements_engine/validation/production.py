"""FSE-05 Mission Control façades for VFQE."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from financial_statements_engine.collection.event_bus import get_bus
from financial_statements_engine.validation.pipeline import validate_draft, validate_draft_path
from financial_statements_engine.validation.schema import (
    ISSUES_RECOMMENDATIONS,
    PROGRAMME,
    QUALITY_TARGETS,
    RECOMMENDATION_POLICY,
    SUBSYSTEM,
    VALIDATOR_VERSION,
    VERSION,
    WORKSTREAM_ID,
)
from financial_statements_engine.validation.store import list_reports, load_report
from financial_statements_engine.store import ensure_dirs
from financial_statements_engine.util import now_iso


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "workstream_id": WORKSTREAM_ID,
        "subsystem": SUBSYSTEM,
        "version": VERSION,
        "validator_version": VALIDATOR_VERSION,
        "quality_targets": QUALITY_TARGETS,
        "capabilities": [
            "input_integrity",
            "structural_validation",
            "accounting_validation",
            "cross_statement_validation",
            "temporal_validation",
            "statistical_validation",
            "sector_rules",
            "quality_scoring",
            "approval_decision",
            "validated_facts_publish",
            "mission_control",
        ],
        "consumes": ["canonical_draft", "parse_manifest", "coverage_matrix", "metric_registry"],
        "never_reads_raw_evidence": True,
        "never_edits_drafts": True,
        "never_reparses": True,
        "issues_recommendations": ISSUES_RECOMMENDATIONS,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "spec": "docs/FSE_05_VALIDATION_FINANCIAL_QUALITY_ENGINE.md",
        "as_of": now_iso(),
    }


def dashboard() -> dict[str, Any]:
    reports = list_reports(limit=200)
    by_status: dict[str, int] = defaultdict(int)
    grades: dict[str, int] = defaultdict(int)
    failed_rules: dict[str, int] = defaultdict(int)
    latencies = []
    for r in reports:
        st = (r.get("approval") or {}).get("approval_status") or "UNKNOWN"
        by_status[st] += 1
        g = (r.get("quality_score") or {}).get("grade")
        if g:
            grades[str(g)] += 1
        latencies.append(float(r.get("processing_time_ms") or 0.0))
        for f in r.get("errors") or []:
            failed_rules[str(f.get("rule_id"))] += 1
        for f in r.get("critical_errors") or []:
            failed_rules[str(f.get("rule_id"))] += 1

    qdir = ensure_dirs() / "parsing" / "validation" / "quarantine"
    quarantined_n = sum(1 for _ in qdir.rglob("*.json")) if qdir.exists() else 0
    events = [e for e in get_bus().tail(300) if "validation." in str(e.get("event_type"))]

    approved = by_status.get("APPROVED", 0) + by_status.get("APPROVED_WITH_WARNINGS", 0)
    total = len(reports) or 1
    return {
        "status": "ok",
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "validation_queue_n": by_status.get("QUARANTINED", 0),
        "approval_rates": {
            "approved_pct": round(100.0 * approved / total, 4),
            "rejected_pct": round(100.0 * by_status.get("REJECTED", 0) / total, 4),
            "quarantined_pct": round(100.0 * by_status.get("QUARANTINED", 0) / total, 4),
        },
        "failure_rates": dict(by_status),
        "quality_score_distribution": dict(grades),
        "common_rule_failures": dict(sorted(failed_rules.items(), key=lambda kv: -kv[1])[:20]),
        "validation_latency_ms_avg": round(sum(latencies) / len(latencies), 3) if latencies else 0.0,
        "quarantined_drafts": quarantined_n,
        "reports_indexed": len(reports),
        "recent_validation_events": events[-30:],
        "issues_recommendations": False,
        "as_of": now_iso(),
    }


def run_validation(draft: dict[str, Any], *, context: dict[str, Any] | None = None, publish: bool = True) -> dict[str, Any]:
    return validate_draft(draft, context=context, publish_on_approve=publish)


def run_validation_file(path: str, *, publish: bool = True) -> dict[str, Any]:
    return validate_draft_path(path, publish_on_approve=publish)


def reports_for(ticker: str | None = None) -> dict[str, Any]:
    rows = list_reports(ticker=ticker, limit=100)
    return {"ok": True, "n": len(rows), "reports": rows, "issues_recommendations": False}


def report_detail(ticker: str, validation_id: str) -> dict[str, Any]:
    row = load_report(ticker, validation_id)
    if not row:
        return {"ok": False, "error": "validation_not_found"}
    return {"ok": True, "report": row, "issues_recommendations": False}
