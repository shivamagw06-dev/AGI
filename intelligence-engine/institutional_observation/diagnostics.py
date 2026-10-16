"""IO-01 diagnostics and quality gates."""

from __future__ import annotations

from typing import Any, Sequence

from institutional_observation.observation import InstitutionalObservation
from institutional_observation.schema import IO_VERSION, IO_WORKSTREAM_ID


def quality_gates(observation: InstitutionalObservation) -> tuple[dict[str, bool], list[str]]:
    errors: list[str] = []
    if not observation.evidence_snapshot_id and not observation.silent:
        # Baseline may lack snapshot briefly — require for emitted observations
        if observation.severity != "ignore":
            errors.append("no evidence")
    if not observation.severity:
        errors.append("no severity")
    if not observation.affected_entities and not observation.silent:
        errors.append("no impact")
    if not observation.lineage:
        errors.append("no lineage")
    if not observation.recommended_action:
        errors.append("no recommendation")
    if not observation.diagnostics:
        errors.append("no diagnostics")

    gates = {
        "has_evidence": bool(observation.evidence_snapshot_id) or observation.silent,
        "has_severity": bool(observation.severity),
        "has_impact": bool(observation.affected_entities) or observation.silent,
        "has_lineage": bool(observation.lineage),
        "has_recommended_action": bool(observation.recommended_action),
        "has_diagnostics": bool(observation.diagnostics),
    }
    return gates, errors


def validate_observation(observation: InstitutionalObservation) -> list[str]:
    _, errors = quality_gates(observation)
    return errors


def build_diagnostics(
    observations: Sequence[InstitutionalObservation],
    *,
    ticker: str = "",
    latency_ms: float = 0.0,
) -> dict[str, Any]:
    rows = list(observations or [])
    return {
        "workstream_id": IO_WORKSTREAM_ID,
        "version": IO_VERSION,
        "ticker": ticker,
        "observation_count": len(rows),
        "critical_count": sum(1 for o in rows if o.severity == "critical"),
        "high_count": sum(1 for o in rows if o.severity == "high"),
        "decision_changes": sum(1 for o in rows if o.decision_changed),
        "pending_reviews": sum(1 for o in rows if o.requires_review),
        "observation_latency_ms": round(latency_ms, 4),
        "observation_throughput": len(rows),
        "llm": False,
    }
