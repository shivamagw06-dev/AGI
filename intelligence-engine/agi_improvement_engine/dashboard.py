"""Structured operational dashboard for improvement sessions."""

from __future__ import annotations

import json
from typing import Any


def build_dashboard(report: dict[str, Any]) -> dict[str, Any]:
    dims = report.get("dimension_weighted_averages") or {}
    return {
        "session_id": report.get("session_id"),
        "attempted": report.get("started_questions"),
        "passed": report.get("passed"),
        "failed": report.get("failed"),
        "weak": max(0, int(report.get("completed") or 0) - int(report.get("passed") or 0)),
        "critical_failures": report.get("critical_failures"),
        "pass_rate_pct": report.get("pass_rate"),
        "average_score": report.get("average_score"),
        "entity_accuracy": dims.get("entity_correctness"),
        "numerical_accuracy": dims.get("numerical_accuracy"),
        "citation_accuracy": dims.get("evidence_support"),
        "freshness": dims.get("freshness"),
        "average_latency_ms": report.get("average_latency_ms"),
        "model_calls": report.get("model_calls"),
        "input_tokens": report.get("input_tokens"),
        "output_tokens": report.get("output_tokens"),
        "estimated_cost_usd": report.get("estimated_api_cost_usd"),
        "fixes_proposed": 0,
        "regressions_found": 0,
        "top_root_causes": report.get("top_root_causes"),
        "companies_covered": report.get("companies_covered"),
        "sectors_covered": report.get("sectors_covered"),
    }


def log_dashboard(report: dict[str, Any]) -> None:
    payload = build_dashboard(report)
    print("[agi-improvement-dashboard] " + json.dumps(payload, ensure_ascii=False), flush=True)
