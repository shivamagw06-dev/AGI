"""AGI v4.0 Phase 5 Sprint 5.5 — Institutional Learning Office (ILO).

Final Office module. Process memory — not Knowledge Factory market facts.
"""

from __future__ import annotations

from typing import Any

ILO_VERSION = "institutional-learning-office-v1.0.0"
LEARNING_SCHEMA_VERSION = "ilo-learning-schema-v1.0.0"
PROGRAMME = (
    "AGI v4.0 – Phase 5 Institutional Investment Office · Sprint 5.5 "
    "Institutional Learning Office"
)
MODULE_CODE = "ILO"
COMPANY = "AGI"
PRODUCT_LINE = "Institutional Investment Office"
OWNER = "AGI Investment Office"

FREEZE_LOCKS: dict[str, Any] = {
    "judgment_stack_v36": True,
    "investment_thesis": True,
    "decision_office": True,
    "portfolio_office": True,
    "monitoring_office": True,
    "process_memory_not_knowledge_factory": True,
    "does_not_update_knowledge_factory": True,
    "does_not_mutate_thesis": True,
    "does_not_mutate_decision": True,
    "does_not_mutate_portfolio": True,
    "does_not_mutate_monitoring_events": True,
    "no_orders": True,
    "no_positions": True,
    "no_execution": True,
    "soft_wire_only": True,
    "deterministic_only": True,
    "no_llm_learning_inflation": True,
    "final_office_module": True,
    "no_sprint_5_6": True,
}

LEARNING_CATEGORIES: tuple[str, ...] = (
    "Evidence",
    "Framework",
    "Hypothesis",
    "Committee",
    "Monitoring",
    "Decision",
    "Portfolio",
    "Timing",
    "Macro",
    "Risk",
)

ROOT_CAUSE_BUCKETS: tuple[str, ...] = (
    "Evidence",
    "Timing",
    "Macro",
    "Management",
    "Valuation",
    "Catalyst",
    "Execution",
    "Hypothesis",
    "Decision Process",
    "Unknown",
)

OUTCOME_LABELS: tuple[str, ...] = (
    "Correct",
    "Partially Correct",
    "Incorrect",
    "Inconclusive",
    "Process Observation",
)

LEARNING_FIELDS: tuple[str, ...] = (
    "learning_id",
    "thesis_id",
    "decision_id",
    "portfolio_id",
    "outcome",
    "expected",
    "actual",
    "difference",
    "root_cause",
    "lesson",
    "future_guidance",
    "confidence_change",
    "linked_monitoring_events",
    "linked_evidence",
    "learning_version",
)
