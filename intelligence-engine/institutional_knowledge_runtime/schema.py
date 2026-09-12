"""Institutional Knowledge Runtime (IKR) v1.0 — schema constants."""

from __future__ import annotations

from typing import Any

IKR_VERSION = "ikr-v1.0.0"
PROGRAMME = "AGI Institutional Knowledge Runtime — Knowledge Execution Layer"
MODULE_CODE = "IKR"

ASSERTION_STATES: tuple[str, ...] = (
    "SUPPORTED",
    "PARTIAL",
    "CONTRADICTED",
    "UNKNOWN",
    "UNDER_REVIEW",
    "STALE",
    "DEPRECATED",
)

# IKO claim states not in IKR spec map 1:1
IKO_TO_ASSERTION_STATE: dict[str, str] = {
    "SUPPORTED": "SUPPORTED",
    "ANSWERED": "PARTIAL",
    "PARTIAL": "PARTIAL",
    "CONTRADICTED": "CONTRADICTED",
    "UNKNOWN": "UNKNOWN",
    "UNDER_REVIEW": "UNDER_REVIEW",
    "STALE": "STALE",
}

PIPELINE_STEPS: tuple[str, ...] = (
    "load_object",
    "load_assertions",
    "resolve_dependencies",
    "resolve_evidence",
    "resolve_contradictions",
    "evaluate_monitoring",
    "calculate_confidence",
    "return_validated",
)

CONFIDENCE_WEIGHTS: dict[str, float] = {
    "evidence_quality": 0.30,
    "evidence_freshness": 0.20,
    "coverage": 0.20,
    "historical_consistency": 0.15,
    "contradiction_penalty": 0.10,
    "monitoring_health": 0.05,
}

APPROVED_WRITERS: tuple[str, ...] = (
    "evidence_pipeline",
    "workflow_completion",
    "decision_memory",
    "monitoring_engine",
    "manual_analyst_review",
    "investment_os",
)

IKR_OBJECT_REGISTRY: dict[str, dict[str, Any]] = {
    "company": {"loader": "institutional_knowledge_object", "implemented": True},
    "sector": {"loader": None, "implemented": False},
    "macro": {"loader": None, "implemented": False},
    "portfolio": {"loader": None, "implemented": False},
    "management": {"loader": None, "implemented": False},
    "theme": {"loader": None, "implemented": False},
    "commodity": {"loader": None, "implemented": False},
    "country": {"loader": None, "implemented": False},
}

DEPENDENCY_DOWNGRADE_STATES: frozenset[str] = frozenset({"CONTRADICTED", "STALE", "DEPRECATED", "UNKNOWN"})
