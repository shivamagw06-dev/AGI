"""AGI Phase 4 Sprint 4.4 — Institutional Committee Reasoning (ICR)."""

from __future__ import annotations

from typing import Any

ICR_VERSION = "institutional-committee-reasoning-v1.0.0"
COMMITTEE_VERSION = "icr-committee-profile-v1.0.0"
PROGRAMME = (
    "AGI v3.6 – Phase 4 Analytical Depth · Sprint 4.4 "
    "Institutional Committee Reasoning"
)
MODULE_CODE = "ICR"
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
    "soft_wire_only": True,
    "deterministic_only": True,
    "no_llm_committee": True,
    "no_voting_engine": True,
    "no_fabricated_consensus": True,
    "conflicts_retained": True,
}

CASE_ROLES: tuple[str, ...] = ("bull", "base", "bear")

# InstitutionalCommitteeReport fields
REPORT_FIELDS: tuple[str, ...] = (
    "bull_case",
    "base_case",
    "bear_case",
    "committee_summary",
    "preferred_case",
    "alternative_cases",
    "probability_distribution",
    "confidence",
    "major_uncertainties",
    "key_disagreements",
    "missing_evidence",
    "committee_version",
    "citations",
)

# Per-case required fields
CASE_FIELDS: tuple[str, ...] = (
    "case_name",
    "case_type",
    "hypothesis_id",
    "supporting_evidence",
    "contradictory_evidence",
    "underlying_assumptions",
    "required_conditions",
    "key_catalysts",
    "key_risks",
    "invalidation_conditions",
    "confidence",
    "probability",
    "evidence_coverage",
    "historical_analogues",
    "framework_alignment",
    "missing_evidence",
)

UPSIDE_CUES: tuple[str, ...] = (
    "growth",
    "premium",
    "expansion",
    "beat",
    "improvement",
    "strength",
    "superior",
    "higher roe",
    "pricing power",
    "franchise",
    "optionality",
    "re-rating",
    "recovery",
    "margin expansion",
)

DOWNSIDE_CUES: tuple[str, ...] = (
    "decline",
    "weakness",
    "pressure",
    "miss",
    "disappointment",
    "risk",
    "deterioration",
    "expensive",
    "compression",
    "inflation",
    "stress",
    "cut guidance",
    "execution issues",
    "mix deterioration",
)
