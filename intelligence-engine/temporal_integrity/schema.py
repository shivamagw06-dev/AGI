"""AGI Phase 3 Sprint 3.5 — Temporal Integrity & Replay Certification (TIRC)."""

from __future__ import annotations

from typing import Any

TIRC_VERSION = "temporal-integrity-v1.0.0"
PROGRAMME = "AGI v3.5 – Phase 3 Quality Programme · Sprint 3.5 Temporal Integrity & Replay Certification"
MODULE_CODE = "TIRC"
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
    "soft_wire_only": True,
    "deterministic_only": True,
    "no_silent_substitution": True,
    "temporal_validation_only": True,
}

TEMPORAL_CONTRACT_FIELDS: tuple[str, ...] = (
    "object_id",
    "available_from",
    "effective_date",
    "announcement_date",
    "observation_date",
    "source_timestamp",
    "replay_timestamp",
    "allowed_as_of",
    "temporal_status",
    "reason_if_rejected",
)

TEMPORAL_STATUS = ("allowed", "rejected", "unknown", "n/a")

CERTIFICATION_TARGETS: dict[str, Any] = {
    "future_leakage_count": 0,
    "replay_accuracy_pct": 100.0,
    "deterministic_replay": True,
}
