"""IEL — Institutional Evaluation Lab schemas (Phase 3 Sprint 3.1)."""

from __future__ import annotations

from typing import Any

IEL_VERSION = "institutional-evaluation-lab-v1.1.0"
PROGRAMME = "AGIB v3.6 – Phase 3 Quality Programme · Institutional Evaluation Lab"
MODULE_CODE = "IEL"

FREEZE_LOCKS: dict[str, Any] = {
    "knowledge_factory": True,
    "governance_internals": True,
    "committees": True,
    "planner": True,
    "reasoning_frozen": True,
    "soft_wire_only": True,
    "deterministic_judges_only": True,
    "no_llm_grading": True,
    "measurement_first": True,
    "augments_not_replaces_product": True,
}

# Stopping-condition targets (Quality Programme north star)
QUALITY_TARGETS: dict[str, Any] = {
    "cio_benchmark": 9.0,
    "benchmark_1000_pass_pct": 90.0,
    "replay_accuracy_pct": 100.0,
    "framework_selection_pct": 98.0,
    "unsupported_claims": 0,
    "hallucinated_evidence": 0,
    "live_collector_certification_pct": 100.0,
    "phase1_golden_n": 200,
    "golden_gate_pass_pct": 80.0,
    "golden_qa_pass_pct": 95.0,
    "golden_unexpected_drift_max": 5,
}

CATEGORIES: tuple[str, ...] = (
    "company",
    "industry",
    "macro",
    "government",
    "accounting",
    "valuation",
    "documents",
    "risk",
    "portfolio",
    "historical_replay",
    "cross_domain",
)

DIFFICULTIES: tuple[str, ...] = ("easy", "medium", "hard", "expert")

JUDGE_DIMENSIONS: tuple[str, ...] = (
    "intent",
    "framework",
    "playbook",
    "evidence",
    "memory",
    "confidence",
    "replay",
    "unsupported_claims",
    "hallucinated_evidence",
)

# Independent Phase 4/5 metrics (not in DIMENSION_WEIGHTS — do not move CIO)
INDEPENDENT_METRICS: tuple[str, ...] = (
    "hypothesis_quality",
    "committee_quality",
    "confidence_quality",
    "thesis_quality",
    "decision_quality",
    "portfolio_quality",
    "monitoring_quality",
    "learning_quality",
)

# Weighted contribution to per-question score (0–100)
DIMENSION_WEIGHTS: dict[str, float] = {
    "intent": 0.16,
    "framework": 0.16,
    "playbook": 0.12,
    "evidence": 0.16,
    "memory": 0.10,
    "confidence": 0.08,
    "replay": 0.10,
    "unsupported_claims": 0.06,
    "hallucinated_evidence": 0.06,
}
