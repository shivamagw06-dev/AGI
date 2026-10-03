"""ICE-01 committee engine — assemble InstitutionalCommitteeResolution."""

from __future__ import annotations

import hashlib
from typing import Any, Optional

from institutional_committee.action_items import build_action_items, follow_up_schedule
from institutional_committee.agenda import build_agenda
from institutional_committee.models import InstitutionalCommitteeResolution
from institutional_committee.resolutions import (
    build_conditions,
    build_rationale,
    review_date_for_status,
)
from institutional_committee.schema import (
    COMMITTEE_ENGINE_VERSION,
    DEFAULT_COMMITTEE_ID,
    LINEAGE_CHAIN,
    VALIDATOR_VERSION,
)
from institutional_committee.voting import cast_votes, resolve_outcome

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def _resolution_id(portfolio_id: str, decision_id: str, version: int, status: str) -> str:
    raw = f"{portfolio_id}|{decision_id}|{version}|{status}|{COMMITTEE_ENGINE_VERSION}"
    return f"ice-{portfolio_id.lower()}-{hashlib.sha256(raw.encode()).hexdigest()[:12]}"


def _as_dict(obj: Any) -> dict[str, Any]:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return dict(obj)
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    return {}


def generate_committee_resolution(
    *,
    portfolio_decision: Any,
    portfolio_risk: Any = None,
    policy_assessment: Any = None,
    previous_version: int = 0,
    committee_id: str = DEFAULT_COMMITTEE_ID,
) -> InstitutionalCommitteeResolution:
    """
    Govern a CIO-01 portfolio decision.

    Does not mutate company decisions, PRE-01 risk, PCE-01 policy, or the CIO decision itself.
    """
    decision = _as_dict(portfolio_decision)
    risk = _as_dict(portfolio_risk)
    policy = _as_dict(policy_assessment)

    portfolio_id = str(
        decision.get("portfolio_id")
        or getattr(portfolio_decision, "portfolio_id", "")
        or ""
    )
    decision_id = str(
        decision.get("decision_id") or getattr(portfolio_decision, "decision_id", "") or ""
    )
    recommendation = str(
        decision.get("recommendation")
        or getattr(portfolio_decision, "recommendation", "")
        or ""
    )

    risk_id = str(
        decision.get("portfolio_risk_id")
        or risk.get("risk_id")
        or getattr(portfolio_risk, "risk_id", "")
        or ""
    )
    overall_risk = str(
        decision.get("overall_risk")
        or risk.get("overall_risk")
        or getattr(portfolio_risk, "overall_risk", "")
        or ""
    )
    policy_id = str(
        decision.get("policy_id")
        or policy.get("policy_id")
        or getattr(policy_assessment, "policy_id", "")
        or ""
    )
    policy_status = str(
        decision.get("policy_status")
        or policy.get("overall_status")
        or getattr(policy_assessment, "overall_status", "")
        or ""
    )

    risk_summary = decision.get("portfolio_risk_summary") or {}
    if not risk_summary and risk:
        risk_summary = {
            "worst_stress": (
                min(
                    risk.get("stress_results") or [{"portfolio_impact_pct": 0}],
                    key=lambda s: float(s.get("portfolio_impact_pct") or 0),
                )
                if risk.get("stress_results")
                else None
            )
        }

    policy_summary = decision.get("policy_summary") or {}
    violations = list(policy.get("violations") or policy_summary.get("violations") or [])
    if not violations and policy_summary.get("primary_violation"):
        violations = [policy_summary["primary_violation"]]
    violation_count = int(
        policy.get("violation_count")
        or policy_summary.get("violation_count")
        or len(violations)
    )

    alloc_actions = list(decision.get("allocation_actions") or [])
    if not alloc_actions and hasattr(portfolio_decision, "allocation_actions"):
        alloc_actions = [
            a.to_dict() if hasattr(a, "to_dict") else dict(a)
            for a in (portfolio_decision.allocation_actions or ())
        ]
    material_trim = any(
        float(a.get("to_weight") or 0) < float(a.get("from_weight") or 0)
        and str(a.get("ticker") or "") != "CASH"
        for a in alloc_actions
    )

    votes = cast_votes(
        overall_risk=overall_risk,
        policy_status=policy_status,
        violation_count=violation_count,
        recommendation=recommendation,
        allocation_action_count=len(alloc_actions),
        material_trim=material_trim,
        worst_stress=risk_summary.get("worst_stress"),
    )
    status, outcome = resolve_outcome(votes)

    monitoring = decision.get("monitoring_plan") or {}
    reviews = list(monitoring.get("required_reviews") or [])

    agenda = build_agenda(
        portfolio_id=portfolio_id,
        overall_risk=overall_risk,
        policy_status=policy_status,
        violations=violations,
        recommendation=recommendation,
        allocation_actions=alloc_actions,
        monitoring_reviews=reviews,
        decision_id=decision_id,
        risk_id=risk_id,
        policy_id=policy_id,
    )

    actions = build_action_items(
        allocation_actions=alloc_actions,
        policy_actions=list(policy.get("required_actions") or policy_summary.get("required_actions") or []),
        policy_violations=violations,
        status=status,
        recommendation=recommendation,
    )
    conditions = build_conditions(
        status=status,
        actions=actions,
        policy_violations=violations,
    )
    rationale = build_rationale(
        votes=votes,
        recommendation=recommendation,
        policy_status=policy_status,
        overall_risk=overall_risk,
        status=status,
    )
    follow_ups = follow_up_schedule(
        status=status,
        agenda_categories=[i.category for i in agenda],
        has_banking=any(
            "bank" in str(a.get("ticker") or "").lower()
            or "bank" in str(a.get("reason") or "").lower()
            for a in alloc_actions
        ),
    )

    generated_at = now_iso()
    version = int(previous_version or 0) + 1
    rid = _resolution_id(portfolio_id, decision_id, version, status)

    return InstitutionalCommitteeResolution(
        committee_id=committee_id or DEFAULT_COMMITTEE_ID,
        resolution_id=rid,
        resolution_version=version,
        portfolio_id=portfolio_id,
        portfolio_decision_id=decision_id,
        generated_at=generated_at,
        status=status,
        outcome=outcome,
        votes=votes,
        rationale=rationale,
        required_actions=actions,
        follow_up_items=follow_ups,
        conditions=conditions,
        review_date=review_date_for_status(status, generated_at),
        agenda=agenda,
        diagnostics=None,
        lineage=LINEAGE_CHAIN,
        portfolio_risk_id=risk_id,
        policy_id=policy_id,
        policy_status=policy_status,
        overall_risk=overall_risk,
        decision_recommendation=recommendation,
        committee_engine_version=COMMITTEE_ENGINE_VERSION,
        validator_version=VALIDATOR_VERSION,
        llm=False,
        mutates_upstream=False,
    )
