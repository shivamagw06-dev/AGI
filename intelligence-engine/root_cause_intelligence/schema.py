"""RCI — Root Cause Intelligence schemas (Phase 3 Sprint 3.2)."""

from __future__ import annotations

from typing import Any

RCI_VERSION = "root-cause-intelligence-v1.0.0"
PROGRAMME = "AGIB v3.6 – Phase 3 Quality Programme · Sprint 3.2 Root Cause Intelligence"
MODULE_CODE = "RCI"

FREEZE_LOCKS: dict[str, Any] = {
    "knowledge_factory": True,
    "governance_internals": True,
    "reasoning_frozen": True,
    "soft_wire_only": True,
    "deterministic_only": True,
    "no_llm_diagnosis": True,
    "measurement_driven_fixes": True,
    "does_not_patch_selectors_yet": True,  # Sprint 3.3 applies patches
}

SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}

# Map judge root causes → engineering owner / next sprint
CAUSE_OWNERS: dict[str, str] = {
    "framework_mismatch": "sprint_3_3_framework_optimisation",
    "intent_mismatch": "sprint_3_4_intent_optimisation",
    "playbook_mismatch": "sprint_3_3_framework_optimisation",
    "evidence_cues_miss": "sprint_3_5_evidence_weighting",
    "empty_evidence_graph": "sprint_3_5_evidence_weighting",
    "memory_miss_on_analog_question": "imai_seed_expansion",
    "future_leakage": "replay_integrity",
    "fabricated_or_invented": "quality_gates",
    "quality_gate_fail": "quality_gates",
    "confidence_band_unexpected": "confidence_calibration",
    "as_of_miss": "replay_integrity",
}

QUALITY_TARGETS: dict[str, Any] = {
    "iel_pass_pct": 95.0,
    "framework_accuracy_pct": 98.0,
    "intent_accuracy_pct": 99.0,
    "hallucinated_evidence": 0,
    "replay_correctness_pct": 100.0,
}
