"""Workflow definitions — metadata only; handlers soft-wire externally."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from institutional_scheduler.schema import DEFAULT_RETRY, DEFAULT_TIMEOUT_SECONDS, SCHEDULER_VERSION

# Morning DAG workflows in dependency order (parallel peers share level).
WORKFLOWS: dict[str, dict[str, Any]] = {
    "universe_update": {
        "workflow_id": "universe_update",
        "name": "Universe Update",
        "dependencies": [],
        "priority": 10,
        "level": 0,
        "retry_policy": DEFAULT_RETRY,
        "timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
        "version": SCHEDULER_VERSION,
        "critical": True,
    },
    "historical_update": {
        "workflow_id": "historical_update",
        "name": "Historical Update",
        "dependencies": ["universe_update"],
        "priority": 20,
        "level": 1,
        "retry_policy": DEFAULT_RETRY,
        "timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
        "version": SCHEDULER_VERSION,
        "critical": False,
    },
    "company_intelligence": {
        "workflow_id": "company_intelligence",
        "name": "Company Intelligence",
        "dependencies": ["historical_update"],
        "priority": 30,
        "level": 2,
        "retry_policy": DEFAULT_RETRY,
        "timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
        "version": SCHEDULER_VERSION,
        "critical": True,
    },
    "government_intelligence": {
        "workflow_id": "government_intelligence",
        "name": "Government Intelligence",
        "dependencies": ["historical_update"],
        "priority": 30,
        "level": 2,
        "retry_policy": DEFAULT_RETRY,
        "timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
        "version": SCHEDULER_VERSION,
        "critical": False,
    },
    "corporate_events": {
        "workflow_id": "corporate_events",
        "name": "Corporate Events",
        "dependencies": ["company_intelligence"],
        "priority": 40,
        "level": 3,
        "retry_policy": DEFAULT_RETRY,
        "timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
        "version": SCHEDULER_VERSION,
        "critical": False,
    },
    "industry_intelligence": {
        "workflow_id": "industry_intelligence",
        "name": "Industry Intelligence",
        "dependencies": ["company_intelligence"],
        "priority": 50,
        "level": 4,
        "retry_policy": DEFAULT_RETRY,
        "timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
        "version": SCHEDULER_VERSION,
        "critical": False,
    },
    "economic_relationships": {
        "workflow_id": "economic_relationships",
        "name": "Economic Relationships",
        "dependencies": ["industry_intelligence"],
        "priority": 60,
        "level": 5,
        "retry_policy": DEFAULT_RETRY,
        "timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
        "version": SCHEDULER_VERSION,
        "critical": False,
    },
    "alternative_data": {
        "workflow_id": "alternative_data",
        "name": "Alternative Data",
        "dependencies": ["economic_relationships"],
        "priority": 70,
        "level": 6,
        "retry_policy": {**DEFAULT_RETRY, "max_attempts": 2},
        "timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
        "version": SCHEDULER_VERSION,
        "critical": False,
    },
    "market_expectations": {
        "workflow_id": "market_expectations",
        "name": "Market Expectations",
        "dependencies": ["company_intelligence", "alternative_data"],
        "priority": 80,
        "level": 7,
        "retry_policy": DEFAULT_RETRY,
        "timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
        "version": SCHEDULER_VERSION,
        "critical": False,
    },
    "evidence_pack_generation": {
        "workflow_id": "evidence_pack_generation",
        "name": "Evidence Pack Generation",
        "dependencies": ["company_intelligence", "market_expectations"],
        "priority": 90,
        "level": 8,
        "retry_policy": DEFAULT_RETRY,
        "timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
        "version": SCHEDULER_VERSION,
        "critical": True,
    },
    "coverage_validation": {
        "workflow_id": "coverage_validation",
        "name": "Coverage Validation",
        "dependencies": ["evidence_pack_generation"],
        "priority": 100,
        "level": 9,
        "retry_policy": {"max_attempts": 1, "backoff_seconds": [0]},
        "timeout_seconds": 120,
        "version": SCHEDULER_VERSION,
        "critical": True,
    },
    "quality_gates": {
        "workflow_id": "quality_gates",
        "name": "Quality Gates",
        "dependencies": ["coverage_validation"],
        "priority": 110,
        "level": 10,
        "retry_policy": {"max_attempts": 1, "backoff_seconds": [0]},
        "timeout_seconds": 60,
        "version": SCHEDULER_VERSION,
        "critical": True,
    },
    "mission_control": {
        "workflow_id": "mission_control",
        "name": "Mission Control Update",
        "dependencies": ["quality_gates"],
        "priority": 120,
        "level": 11,
        "retry_policy": DEFAULT_RETRY,
        "timeout_seconds": 120,
        "version": SCHEDULER_VERSION,
        "critical": False,
    },
    "daily_health": {
        "workflow_id": "daily_health",
        "name": "Daily Health",
        "dependencies": ["quality_gates"],
        "priority": 120,
        "level": 11,
        "retry_policy": DEFAULT_RETRY,
        "timeout_seconds": 120,
        "version": SCHEDULER_VERSION,
        "critical": True,
    },
    "research_queue": {
        "workflow_id": "research_queue",
        "name": "Research Queue",
        "dependencies": ["mission_control", "daily_health"],
        "priority": 130,
        "level": 12,
        "retry_policy": DEFAULT_RETRY,
        "timeout_seconds": 60,
        "version": SCHEDULER_VERSION,
        "critical": False,
    },
    "morning_reports": {
        "workflow_id": "morning_reports",
        "name": "Morning Reports",
        "dependencies": ["research_queue"],
        "priority": 140,
        "level": 13,
        "retry_policy": DEFAULT_RETRY,
        "timeout_seconds": 120,
        "version": SCHEDULER_VERSION,
        "critical": False,
    },
    "ready_declaration": {
        "workflow_id": "ready_declaration",
        "name": "READY Declaration",
        "dependencies": ["morning_reports", "quality_gates"],
        "priority": 150,
        "level": 14,
        "retry_policy": {"max_attempts": 1, "backoff_seconds": [0]},
        "timeout_seconds": 30,
        "version": SCHEDULER_VERSION,
        "critical": True,
    },
}


def list_workflows() -> list[dict[str, Any]]:
    stats = {}
    try:
        from institutional_scheduler import store

        stats = store.workflow_stats()
    except Exception:
        stats = {}
    rows = []
    for wf in WORKFLOWS.values():
        row = deepcopy(wf)
        st = stats.get(wf["workflow_id"]) or {}
        row["health_status"] = "unknown"
        row["execution_history"] = st.get("historical_runtime_ms") or []
        row["duration"] = st.get("average_runtime_ms")
        row["success_rate"] = st.get("success_rate")
        rows.append(row)
    rows.sort(key=lambda r: (r.get("level", 0), r.get("priority", 0)))
    return rows


def get_workflow(workflow_id: str) -> dict[str, Any] | None:
    wf = WORKFLOWS.get(workflow_id)
    return deepcopy(wf) if wf else None
