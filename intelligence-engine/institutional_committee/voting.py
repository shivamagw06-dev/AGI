"""ICE-01 deterministic voting desks — structured governance, not people simulation."""

from __future__ import annotations

from typing import Any, Optional

from institutional_committee.models import CommitteeVote


def _risk_vote(overall_risk: str, worst_stress: Optional[dict[str, Any]] = None) -> CommitteeVote:
    risk = (overall_risk or "").strip()
    stress_pct = 0.0
    if worst_stress:
        stress_pct = abs(float(worst_stress.get("portfolio_impact_pct") or 0.0))

    if risk == "Critical" or stress_pct >= 15:
        return CommitteeVote(
            desk="Risk",
            vote="ESCALATE",
            rationale=f"Overall risk {risk or 'elevated'}; worst stress {stress_pct:.1f}%",
        )
    if risk == "High" or stress_pct >= 10:
        return CommitteeVote(
            desk="Risk",
            vote="APPROVE_WITH_CONDITIONS",
            rationale=f"Elevated risk ({risk}); conditions required before full approval",
        )
    if risk == "Moderate":
        return CommitteeVote(
            desk="Risk",
            vote="REQUIRES_REVIEW",
            rationale="Moderate risk — allocation desk review recommended",
        )
    return CommitteeVote(
        desk="Risk",
        vote="APPROVE",
        rationale=f"Risk posture acceptable ({risk or 'Low'})",
    )


def _policy_vote(policy_status: str, violation_count: int = 0) -> CommitteeVote:
    status = (policy_status or "").strip()
    if status == "Critical Breach" or violation_count >= 4:
        return CommitteeVote(
            desk="Policy",
            vote="REJECT",
            rationale=f"Mandate {status or 'breach'} with {violation_count} violations — not approvable",
        )
    if status == "Breach" or violation_count >= 1:
        return CommitteeVote(
            desk="Policy",
            vote="APPROVE_WITH_CONDITIONS",
            rationale=f"Policy {status}: remediation conditions mandatory ({violation_count} violations)",
        )
    if status == "Warning":
        return CommitteeVote(
            desk="Policy",
            vote="REQUIRES_REVIEW",
            rationale="Constraints nearing limits — monitor before full approval",
        )
    return CommitteeVote(
        desk="Policy",
        vote="APPROVE",
        rationale="Portfolio within mandate",
    )


def _allocation_vote(
    recommendation: str,
    *,
    allocation_action_count: int = 0,
    material_trim: bool = False,
) -> CommitteeVote:
    rec = (recommendation or "").strip()
    if rec in {"Review Portfolio"} or (material_trim and allocation_action_count >= 3):
        return CommitteeVote(
            desk="Allocation",
            vote="REQUIRES_REVIEW",
            rationale=f"Material allocation change under '{rec}' — desk review required",
        )
    if rec in {"Reduce Concentration", "Increase Diversification", "Increase Cash", "Reduce Technology"}:
        if allocation_action_count >= 1:
            return CommitteeVote(
                desk="Allocation",
                vote="APPROVE_WITH_CONDITIONS",
                rationale=f"Approve '{rec}' subject to staged rebalance conditions",
            )
        return CommitteeVote(
            desk="Allocation",
            vote="DEFER",
            rationale=f"Recommendation '{rec}' lacks concrete allocation actions — defer",
        )
    if rec in {"Maintain Allocation", "No Action Required"}:
        return CommitteeVote(
            desk="Allocation",
            vote="APPROVE",
            rationale="No material allocation change required",
        )
    return CommitteeVote(
        desk="Allocation",
        vote="REQUIRES_REVIEW",
        rationale=f"Allocation desk to review recommendation '{rec or 'unknown'}'",
    )


def cast_votes(
    *,
    overall_risk: str = "",
    policy_status: str = "",
    violation_count: int = 0,
    recommendation: str = "",
    allocation_action_count: int = 0,
    material_trim: bool = False,
    worst_stress: Optional[dict[str, Any]] = None,
) -> tuple[CommitteeVote, ...]:
    return (
        _risk_vote(overall_risk, worst_stress),
        _policy_vote(policy_status, violation_count),
        _allocation_vote(
            recommendation,
            allocation_action_count=allocation_action_count,
            material_trim=material_trim,
        ),
    )


def resolve_outcome(votes: tuple[CommitteeVote, ...]) -> tuple[str, str]:
    """
    Aggregate desk votes into (status, outcome_summary).

    Priority: REJECT > ESCALATE > DEFER > APPROVE_WITH_CONDITIONS > REQUIRES_REVIEW > APPROVE
    """
    choices = {v.vote for v in votes}
    if "REJECT" in choices:
        return "Rejected", "Committee rejected the portfolio decision pending mandate remediation"
    if "ESCALATE" in choices:
        return "Escalated", "Committee escalated due to critical risk posture"
    if "DEFER" in choices:
        return "Deferred", "Committee deferred pending clearer allocation actions"
    if "APPROVE_WITH_CONDITIONS" in choices:
        return (
            "Approved with Conditions",
            "Committee approved subject to stated remediation conditions",
        )
    if "REQUIRES_REVIEW" in choices:
        return "Pending Review", "Committee requires further desk review before resolution"
    if choices and choices <= {"APPROVE"}:
        return "Approved", "Committee approved the portfolio decision"
    return "Pending Review", "Committee resolution pending"
