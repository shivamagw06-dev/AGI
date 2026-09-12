"""ICE-01 InstitutionalCommitteeResolution — immutable governance object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class CommitteeVote:
    desk: str  # Risk | Policy | Allocation
    vote: str
    rationale: str = ""
    weight: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "desk": self.desk,
            "vote": self.vote,
            "rationale": self.rationale,
            "weight": float(self.weight),
        }


@dataclass(frozen=True)
class CommitteeActionItem:
    action_id: str
    title: str
    detail: str
    owner: str
    due: str
    ticker: str = ""
    from_value: float = 0.0
    to_value: float = 0.0
    priority: str = "medium"  # low | medium | high | critical
    source: str = ""  # policy | allocation | risk | monitoring

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "title": self.title,
            "detail": self.detail,
            "owner": self.owner,
            "due": self.due,
            "ticker": self.ticker,
            "from_value": float(self.from_value),
            "to_value": float(self.to_value),
            "priority": self.priority,
            "source": self.source,
        }


@dataclass(frozen=True)
class AgendaItem:
    item_id: str
    category: str
    title: str
    severity: str
    portfolio_id: str = ""
    reference_id: str = ""
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "category": self.category,
            "title": self.title,
            "severity": self.severity,
            "portfolio_id": self.portfolio_id,
            "reference_id": self.reference_id,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class InstitutionalCommitteeResolution:
    """Authoritative committee governance object — references CIO decision; never mutates it."""

    committee_id: str
    resolution_id: str
    resolution_version: int
    portfolio_id: str
    portfolio_decision_id: str
    generated_at: str
    status: str
    outcome: str
    votes: tuple[CommitteeVote, ...] = ()
    rationale: tuple[str, ...] = ()
    required_actions: tuple[CommitteeActionItem, ...] = ()
    follow_up_items: tuple[str, ...] = ()
    conditions: tuple[str, ...] = ()
    review_date: Optional[str] = None
    agenda: tuple[AgendaItem, ...] = ()
    diagnostics: Optional[dict[str, Any]] = None
    lineage: tuple[str, ...] = (
        "Committee",
        "Resolution",
        "Portfolio Decision",
        "Policy Assessment",
        "Portfolio Risk",
        "Evidence",
    )
    portfolio_risk_id: str = ""
    policy_id: str = ""
    policy_status: str = ""
    overall_risk: str = ""
    decision_recommendation: str = ""
    committee_engine_version: str = ""
    validator_version: str = ""
    llm: bool = False
    mutates_upstream: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "committee_id": self.committee_id,
            "resolution_id": self.resolution_id,
            "resolution_version": int(self.resolution_version),
            "portfolio_id": self.portfolio_id,
            "portfolio_decision_id": self.portfolio_decision_id,
            "generated_at": self.generated_at,
            "status": self.status,
            "outcome": self.outcome,
            "votes": [v.to_dict() for v in self.votes],
            "rationale": list(self.rationale),
            "required_actions": [a.to_dict() for a in self.required_actions],
            "follow_up_items": list(self.follow_up_items),
            "conditions": list(self.conditions),
            "review_date": self.review_date,
            "agenda": [i.to_dict() for i in self.agenda],
            "diagnostics": dict(self.diagnostics or {}),
            "lineage": list(self.lineage),
            "portfolio_risk_id": self.portfolio_risk_id,
            "policy_id": self.policy_id,
            "policy_status": self.policy_status,
            "overall_risk": self.overall_risk,
            "decision_recommendation": self.decision_recommendation,
            "committee_engine_version": self.committee_engine_version,
            "validator_version": self.validator_version,
            "llm": False,
            "mutates_upstream": False,
            "predictive": False,
            "action_count": len(self.required_actions),
            "vote_count": len(self.votes),
        }

    @property
    def is_pending(self) -> bool:
        return self.status == "Pending Review"

    @property
    def is_approved(self) -> bool:
        return self.status in {"Approved", "Approved with Conditions"}
