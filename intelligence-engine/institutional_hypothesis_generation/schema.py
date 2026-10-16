"""AGI Phase 4 Sprint 4.2 — Institutional Hypothesis Generation Engine (IHG)."""

from __future__ import annotations

from typing import Any

IHG_VERSION = "institutional-hypothesis-generation-v1.0.0"
HYPOTHESIS_VERSION = "ihg-hypothesis-catalog-v1.0.0"
PROGRAMME = (
    "AGI v3.6 – Phase 4 Analytical Depth · Sprint 4.2 "
    "Institutional Hypothesis Generation Engine"
)
MODULE_CODE = "IHG"
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
    "soft_wire_only": True,
    "deterministic_only": True,
    "no_llm_hypothesis": True,
    "no_fabricated_hypotheses": True,
    "no_forced_single_winner": True,
}

HYPOTHESIS_CATEGORIES: tuple[str, ...] = (
    "Company",
    "Industry",
    "Macro",
    "Policy",
    "Accounting",
    "CapitalAllocation",
    "Governance",
    "Risk",
    "Valuation",
    "Portfolio",
    "CrossDomain",
    "Replay",
    "Mixed",
)

HYPOTHESIS_STATUSES: tuple[str, ...] = (
    "Active",
    "Preferred",
    "Contested",
    "Rejected",
    "InsufficientEvidence",
)

# InstitutionalHypothesis required fields
HYPOTHESIS_FIELDS: tuple[str, ...] = (
    "hypothesis_id",
    "hypothesis",
    "category",
    "framework",
    "supporting_evidence",
    "contradicting_evidence",
    "weighted_support",
    "weighted_conflict",
    "support_score",
    "conflict_score",
    "overall_score",
    "confidence",
    "status",
    "priority",
    "reason",
    "citations",
    "share",  # plural outcome probability mass (0..1)
)

# Scoring thresholds (deterministic)
REJECT_OVERALL_BELOW = 18.0
WEAK_SUPPORT_BELOW = 12.0
CLEAR_LEADER_GAP = 0.15  # share gap required to mark Preferred vs Contested
MIN_HYPOTHESES = 2
MAX_HYPOTHESES = 5
