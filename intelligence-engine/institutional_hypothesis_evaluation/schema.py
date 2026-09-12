"""AGI Phase 4 Sprint 4.3 — Institutional Hypothesis Evaluation Engine (IHE)."""

from __future__ import annotations

from typing import Any

IHE_VERSION = "institutional-hypothesis-evaluation-v1.0.0"
EVALUATION_VERSION = "ihe-evaluation-profile-v1.0.0"
PROGRAMME = (
    "AGI v3.6 – Phase 4 Analytical Depth · Sprint 4.3 "
    "Institutional Hypothesis Evaluation Engine"
)
MODULE_CODE = "IHE"
COMPANY = "AGI"

FREEZE_LOCKS: dict[str, Any] = {
    "knowledge_factory": True,
    "reasoning_frozen": True,
    "framework_selection": True,
    "intent_resolution": True,
    "playbooks": True,
    "evaluation_lab": True,
    "root_cause_intelligence": True,
    "communication": True,
    "temporal_integrity": True,
    "evidence_graph": True,
    "institutional_memory": True,
    "evidence_weighting": True,
    "hypothesis_generation": True,
    "soft_wire_only": True,
    "deterministic_only": True,
    "no_llm_evaluation": True,
    "no_forced_single_winner": True,
    "conflicts_retained": True,
}

EVALUATION_STATUSES: tuple[str, ...] = (
    "Preferred",
    "Plausible",
    "Rejected",
    "Indeterminate",
)

# Dimension caps (sum = 100 for scorecard readability)
DIMENSION_CAPS: dict[str, float] = {
    "support": 22.0,
    "conflict": 18.0,  # inverted: low conflict → high score
    "coverage": 16.0,
    "historical": 12.0,
    "framework": 10.0,
    "missing_evidence": 10.0,  # inverted: less missing → higher
    "alternative_strength": 6.0,  # inverted: weaker alts → higher
    "explanatory_power": 6.0,
}

# InstitutionalHypothesisReport fields
REPORT_FIELDS: tuple[str, ...] = (
    "preferred_hypothesis",
    "alternative_hypotheses",
    "support_score",
    "conflict_score",
    "coverage_score",
    "historical_score",
    "framework_score",
    "missing_evidence",
    "confidence",
    "evaluation_reason",
    "evaluation_version",
    "citations",
)

# Outcome labels for the pack
OUTCOMES: tuple[str, ...] = (
    "preferred",
    "plausible_set",
    "indeterminate",
    "rejected_all",
    "insufficient_evidence",
)

CLEAR_LEAD_GAP = 8.0  # evaluation_score points for Preferred vs next
BALANCED_GAP = 4.0  # within this → Indeterminate / Plausible set
REJECT_BELOW = 28.0
MIN_CONFIDENCE_WITH_CRITICAL_MISSING = 0.45
