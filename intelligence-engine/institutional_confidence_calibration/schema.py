"""AGI Phase 4 Sprint 4.5 — Institutional Confidence Calibration (ICC)."""

from __future__ import annotations

from typing import Any

ICC_VERSION = "institutional-confidence-calibration-v1.0.0"
CONFIDENCE_VERSION = "icc-confidence-profile-v1.0.0"
PROGRAMME = (
    "AGI v3.6 – Phase 4 Analytical Depth · Sprint 4.5 "
    "Institutional Confidence Calibration"
)
MODULE_CODE = "ICC"
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
    "hypothesis_evaluation": True,
    "committee_reasoning": True,
    "soft_wire_only": True,
    "deterministic_only": True,
    "no_llm_confidence": True,
    "no_manual_confidence": True,
    "fixtures_never_increase": True,
}

# Positive contribution weights (sum = 1.0) before penalties
DIMENSION_WEIGHTS: dict[str, float] = {
    "evidence_quality": 0.16,
    "coverage_score": 0.12,
    "hypothesis_strength": 0.14,
    "hypothesis_separation": 0.10,
    "conflict_score": 0.10,  # inverted: low conflict → high score
    "committee_agreement": 0.14,
    "historical_score": 0.10,
    "framework_consistency": 0.08,
    "integrity_gate": 0.06,  # temporal + replay both true → 100
}

# Report fields required by InstitutionalConfidenceReport
REPORT_FIELDS: tuple[str, ...] = (
    "overall_confidence",
    "confidence_level",
    "evidence_quality",
    "coverage_score",
    "hypothesis_strength",
    "hypothesis_separation",
    "conflict_score",
    "committee_agreement",
    "historical_score",
    "framework_consistency",
    "missing_evidence_penalty",
    "temporal_integrity",
    "replay_integrity",
    "confidence_reason",
    "confidence_version",
)

# Numeric bands — never arbitrary alone; always paired with reason
LEVEL_BANDS: tuple[tuple[int, str], ...] = (
    (90, "Very High"),
    (80, "High"),
    (60, "Moderate"),
    (40, "Low"),
    (0, "Very Low"),
)
