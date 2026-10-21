"""AGI Phase 4 Sprint 4.1 — Institutional Evidence Weighting Engine (IEW)."""

from __future__ import annotations

from typing import Any

IEW_VERSION = "institutional-evidence-weighting-v1.0.0"
WEIGHT_VERSION = "iew-weight-profile-v1.0.0"
PROGRAMME = (
    "AGI v3.6 – Phase 4 Analytical Depth · Sprint 4.1 "
    "Institutional Evidence Weighting Engine"
)
MODULE_CODE = "IEW"
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
    "soft_wire_only": True,
    "deterministic_only": True,
    "no_llm_weighting": True,
    "no_contradiction_resolution": True,
}

# InstitutionalWeightedEvidence required fields
WEIGHTED_EVIDENCE_FIELDS: tuple[str, ...] = (
    "evidence_id",
    "source",
    "document_id",
    "citations",
    "weight_score",
    "credibility_score",
    "materiality_score",
    "freshness_score",
    "quality_score",
    "corroboration_score",
    "analogue_score",
    "temporal_status",
    "confidence_modifier",
    "reason",
    "weight_version",
    "weight_breakdown",
    "ranking_position",
    "exclusion_reason",
)

CONTRADICTION_LABELS = ("higher_weight", "lower_weight", "equal_weight")
