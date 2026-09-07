"""PCE-01 diagnostics payload."""

from __future__ import annotations

from typing import Any, Optional

from institutional_policy.models import InstitutionalPolicyAssessment
from institutional_policy.schema import (
    LINEAGE_CHAIN,
    PCE_VERSION,
    PCE_WORKSTREAM_ID,
    POLICY_ENGINE_VERSION,
    VALIDATOR_VERSION,
)


def build_diagnostics(
    assessment: InstitutionalPolicyAssessment,
    *,
    validation: Optional[dict[str, Any]] = None,
    latency_ms: float = 0.0,
    holding_count: int = 0,
) -> dict[str, Any]:
    return {
        "workstream_id": PCE_WORKSTREAM_ID,
        "version": PCE_VERSION,
        "policy_engine_version": POLICY_ENGINE_VERSION,
        "validator_version": VALIDATOR_VERSION,
        "policy_id": assessment.policy_id,
        "policy_version": assessment.policy_version,
        "portfolio_id": assessment.portfolio_id,
        "profile_id": assessment.profile_id,
        "overall_status": assessment.overall_status,
        "compliance_score": assessment.compliance_score,
        "holding_count": int(holding_count),
        "violation_count": len(assessment.violations),
        "passed_count": len(assessment.passed_constraints),
        "failed_count": len(assessment.failed_constraints),
        "nearing_count": len(assessment.nearing_limits),
        "portfolio_risk_id": assessment.portfolio_risk_id,
        "lineage": list(LINEAGE_CHAIN),
        "latency_ms": round(float(latency_ms), 2),
        "validation": validation or {},
        "llm": False,
        "authoritative": True,
        "governs_cio": True,
    }
