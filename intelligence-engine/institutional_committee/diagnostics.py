"""ICE-01 diagnostics payload."""

from __future__ import annotations

from typing import Any, Optional

from institutional_committee.models import InstitutionalCommitteeResolution
from institutional_committee.schema import (
    COMMITTEE_ENGINE_VERSION,
    ICE_VERSION,
    ICE_WORKSTREAM_ID,
    LINEAGE_CHAIN,
    VALIDATOR_VERSION,
)


def build_diagnostics(
    resolution: InstitutionalCommitteeResolution,
    *,
    validation: Optional[dict[str, Any]] = None,
    latency_ms: float = 0.0,
) -> dict[str, Any]:
    return {
        "workstream_id": ICE_WORKSTREAM_ID,
        "version": ICE_VERSION,
        "committee_engine_version": COMMITTEE_ENGINE_VERSION,
        "validator_version": VALIDATOR_VERSION,
        "resolution_id": resolution.resolution_id,
        "resolution_version": resolution.resolution_version,
        "portfolio_id": resolution.portfolio_id,
        "portfolio_decision_id": resolution.portfolio_decision_id,
        "status": resolution.status,
        "outcome": resolution.outcome,
        "portfolio_risk_id": resolution.portfolio_risk_id,
        "policy_id": resolution.policy_id,
        "vote_count": len(resolution.votes),
        "action_count": len(resolution.required_actions),
        "agenda_count": len(resolution.agenda),
        "lineage": list(LINEAGE_CHAIN),
        "latency_ms": round(float(latency_ms), 2),
        "validation": validation or {},
        "llm": False,
        "predictive": False,
        "mutates_upstream": False,
        "governs_cio": True,
    }
