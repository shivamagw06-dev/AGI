"""Institutional Scheduler schemas — orchestration only."""

from __future__ import annotations

from typing import Any

SCHEDULER_VERSION = "institutional-scheduler-v1.0.0"
PROGRAMME = "AGIB v2.1 – Institutional Scheduler & Morning Operations"
MODULE_CODE = "ISCH"

OPERATIONAL_STATES: tuple[str, ...] = (
    "INITIALISING",
    "RUNNING",
    "PARTIAL_READY",
    "READY",
    "WARNING",
    "FAILED",
    "MAINTENANCE",
)

FREEZE_LOCKS: dict[str, Any] = {
    "phases_1_7": True,
    "knowledge_factory": True,
    "intelligence_packages": True,
    "ask_pipeline": True,
    "governance": True,
    "committees": True,
    "decision_quality": True,
    "continuous_adaptive_learning": True,
    "evidence_factory": True,
    "soft_wire_only": True,
    "no_reasoning": True,
    "no_intelligence": True,
}

DEFAULT_RETRY = {"max_attempts": 3, "backoff_seconds": [1, 2, 4], "partial_retry": True}
DEFAULT_TIMEOUT_SECONDS = 300
