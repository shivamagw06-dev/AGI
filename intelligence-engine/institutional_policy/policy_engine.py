"""PCE-01 policy engine — assemble InstitutionalPolicyAssessment."""

from __future__ import annotations

import hashlib
from typing import Any, Optional

from institutional_portfolio.portfolio_entities import InstitutionalPortfolio
from institutional_policy.compliance import compliance_score, overall_status
from institutional_policy.constraints import evaluate_all_constraints
from institutional_policy.mandates import get_mandate
from institutional_policy.models import InstitutionalPolicyAssessment
from institutional_policy.schema import (
    LINEAGE_CHAIN,
    POLICY_ENGINE_VERSION,
    VALIDATOR_VERSION,
)
from institutional_policy.violations import build_violations, required_actions

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def _policy_id(portfolio_id: str, profile_id: str, version: int, status: str) -> str:
    raw = f"{portfolio_id}|{profile_id}|{version}|{status}|{POLICY_ENGINE_VERSION}"
    return f"pce-{portfolio_id.lower()}-{hashlib.sha256(raw.encode()).hexdigest()[:12]}"


def generate_policy_assessment(
    portfolio: InstitutionalPortfolio,
    *,
    profile_id: str = "family_office",
    portfolio_risk: Any = None,
    previous_version: int = 0,
) -> InstitutionalPolicyAssessment:
    """Evaluate mandate constraints against portfolio + PRE-01 risk."""
    mandate = get_mandate(profile_id)
    results = evaluate_all_constraints(mandate, portfolio, portfolio_risk)

    passed = tuple(r for r in results if r.status == "Pass")
    failed = tuple(r for r in results if r.status == "Violation")
    nearing = tuple(r for r in results if r.status == "Warning")
    violations = build_violations(results)
    actions = required_actions(violations)

    status = overall_status(violations, nearing)
    score = compliance_score(
        total_constraints=len(results),
        passed=len(passed),
        warnings=len(nearing),
        violations=violations,
    )

    warn_msgs: list[str] = []
    for r in nearing:
        warn_msgs.append(f"Nearing limit: {r.name} actual={r.actual} limit={r.limit}")
    for v in violations:
        warn_msgs.append(f"Violation: {v.name} — {v.required_action}")

    version = int(previous_version or 0) + 1
    risk_id = ""
    if portfolio_risk is not None:
        risk_id = str(getattr(portfolio_risk, "risk_id", "") or "")

    return InstitutionalPolicyAssessment(
        policy_id=_policy_id(portfolio.portfolio_id, mandate.profile_id, version, status),
        portfolio_id=portfolio.portfolio_id,
        policy_version=version,
        generated_at=now_iso(),
        overall_status=status,
        profile_id=mandate.profile_id,
        violations=violations,
        warnings=tuple(warn_msgs),
        passed_constraints=passed,
        failed_constraints=failed,
        nearing_limits=nearing,
        required_actions=actions,
        mandate=mandate.to_dict(),
        compliance_score=score,
        diagnostics=None,
        lineage=LINEAGE_CHAIN,
        portfolio_graph_id=portfolio.graph_id,
        portfolio_risk_id=risk_id,
        policy_engine_version=POLICY_ENGINE_VERSION,
        validator_version=VALIDATOR_VERSION,
        llm=False,
    )


def policy_summary_for_cio(assessment: InstitutionalPolicyAssessment) -> dict[str, Any]:
    """Compact policy dict consumed by CIO-01 decision engine."""
    primary = assessment.violations[0] if assessment.violations else None
    return {
        "policy_id": assessment.policy_id,
        "policy_version": assessment.policy_version,
        "profile_id": assessment.profile_id,
        "overall_status": assessment.overall_status,
        "compliance_score": assessment.compliance_score,
        "violation_count": len(assessment.violations),
        "has_breach": assessment.has_breach,
        "primary_violation": primary.to_dict() if primary else None,
        "required_actions": list(assessment.required_actions),
        "warnings": list(assessment.warnings)[:8],
        "authoritative": True,
        "source": "PCE-01",
    }
