"""FSE-04.1 quality framework production façades."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.collection.event_bus import get_bus
from financial_statements_engine.parsing.quality.benchmarks import run_benchmarks
from financial_statements_engine.parsing.quality.certification import certify_parser
from financial_statements_engine.parsing.quality.manifest import list_manifests
from financial_statements_engine.parsing.quality.replay import replay
from financial_statements_engine.parsing.quality.schema import (
    ISSUES_RECOMMENDATIONS,
    PROGRAMME,
    QUALITY_GATES,
    RECOMMENDATION_POLICY,
    SUBSYSTEM,
    VERSION,
    WORKSTREAM_ID,
)
from financial_statements_engine.parsing.quality.unknown_queue import list_queue
from financial_statements_engine.store import ensure_dirs
from financial_statements_engine.util import now_iso


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "workstream_id": WORKSTREAM_ID,
        "subsystem": SUBSYSTEM,
        "version": VERSION,
        "quality_gates": QUALITY_GATES,
        "capabilities": [
            "parse_manifest",
            "multi_stage_confidence",
            "hierarchical_statement_tree",
            "unknown_metric_review",
            "parser_replay",
            "diff_engine",
            "versioned_events",
            "lineage_graph",
            "parser_certification",
            "benchmark_suite",
        ],
        "extends": "FSE-04",
        "issues_recommendations": ISSUES_RECOMMENDATIONS,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "spec": "docs/FSE_04_1_PARSE_MANIFEST_REPLAY_CERTIFICATION.md",
        "as_of": now_iso(),
    }


def dashboard() -> dict[str, Any]:
    root = ensure_dirs()
    manifests_n = sum(1 for _ in (root / "parsing" / "manifests").rglob("*.json")) if (root / "parsing" / "manifests").exists() else 0
    unknown_open = list_queue(status="open")
    events = [e for e in get_bus().tail(200) if "parse." in str(e.get("event_type")) or "draft." in str(e.get("event_type")) or "unknown_metric" in str(e.get("event_type")) or "parser." in str(e.get("event_type"))]
    return {
        "status": "ok",
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "parser_health": "ok",
        "manifests_indexed": manifests_n,
        "unknown_metric_queue_open": len(unknown_open),
        "recent_quality_events": events[-30:],
        "quality_gates": QUALITY_GATES,
        "issues_recommendations": False,
        "as_of": now_iso(),
    }


def manifests_for(ticker: str) -> dict[str, Any]:
    rows = list_manifests(ticker)
    return {
        "ok": True,
        "ticker": ticker.upper().strip(),
        "n": len(rows),
        "manifests": rows,
        "issues_recommendations": False,
        "as_of": now_iso(),
    }


def unknown_metrics(status: str = "open") -> dict[str, Any]:
    rows = list_queue(status=status if status != "all" else None)
    return {
        "ok": True,
        "status_filter": status,
        "n": len(rows),
        "rows": rows,
        "issues_recommendations": False,
        "as_of": now_iso(),
    }


def run_replay(ticker: str, evidence_id: str, prior_manifest_id: str | None = None) -> dict[str, Any]:
    return replay(ticker=ticker, evidence_id=evidence_id, prior_manifest_id=prior_manifest_id)


def run_certification() -> dict[str, Any]:
    return certify_parser()


def run_benchmark_suite() -> dict[str, Any]:
    return run_benchmarks()
