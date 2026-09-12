"""PCE-01 InstitutionalPolicyAssessment — immutable, versioned governance object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class PolicyConstraint:
    """A single deterministic mandate limit."""

    constraint_id: str
    category: str  # position | sector | cash | diversification | liquidity | risk
    name: str
    operator: str  # max | min
    limit: float
    unit: str = "weight"  # weight | score | days | count | beta | pct
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "constraint_id": self.constraint_id,
            "category": self.category,
            "name": self.name,
            "operator": self.operator,
            "limit": float(self.limit),
            "unit": self.unit,
            "description": self.description,
        }


@dataclass(frozen=True)
class ConstraintResult:
    constraint_id: str
    category: str
    name: str
    operator: str
    limit: float
    actual: float
    status: str  # Pass | Warning | Violation
    headroom: float
    detail: str = ""
    action: str = ""
    action_ticker: str = ""
    from_value: float = 0.0
    to_value: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "constraint_id": self.constraint_id,
            "category": self.category,
            "name": self.name,
            "operator": self.operator,
            "limit": float(self.limit),
            "actual": float(self.actual),
            "status": self.status,
            "headroom": float(self.headroom),
            "detail": self.detail,
            "action": self.action,
            "action_ticker": self.action_ticker,
            "from_value": float(self.from_value),
            "to_value": float(self.to_value),
            "exceeded": self.status == "Violation",
        }


@dataclass(frozen=True)
class PolicyViolation:
    constraint_id: str
    category: str
    name: str
    severity: str  # warning | breach | critical
    actual: float
    limit: float
    detail: str
    required_action: str
    action_ticker: str = ""
    from_value: float = 0.0
    to_value: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "constraint_id": self.constraint_id,
            "category": self.category,
            "name": self.name,
            "severity": self.severity,
            "actual": float(self.actual),
            "limit": float(self.limit),
            "detail": self.detail,
            "required_action": self.required_action,
            "action_ticker": self.action_ticker,
            "from_value": float(self.from_value),
            "to_value": float(self.to_value),
        }


@dataclass(frozen=True)
class MandateProfile:
    profile_id: str
    label: str
    description: str
    constraints: tuple[PolicyConstraint, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "label": self.label,
            "description": self.description,
            "constraint_count": len(self.constraints),
            "constraints": [c.to_dict() for c in self.constraints],
        }


@dataclass(frozen=True)
class InstitutionalPolicyAssessment:
    """Authoritative policy / mandate compliance object for the Investment Office."""

    policy_id: str
    portfolio_id: str
    policy_version: int
    generated_at: str
    overall_status: str
    profile_id: str
    violations: tuple[PolicyViolation, ...] = ()
    warnings: tuple[str, ...] = ()
    passed_constraints: tuple[ConstraintResult, ...] = ()
    failed_constraints: tuple[ConstraintResult, ...] = ()
    nearing_limits: tuple[ConstraintResult, ...] = ()
    required_actions: tuple[str, ...] = ()
    mandate: Optional[dict[str, Any]] = None
    compliance_score: int = 100
    diagnostics: Optional[dict[str, Any]] = None
    lineage: tuple[str, ...] = (
        "Portfolio",
        "Holding",
        "Portfolio Risk",
        "Policy Constraint",
        "Company Decision",
        "Reason",
        "Evidence",
    )
    portfolio_graph_id: str = ""
    portfolio_risk_id: str = ""
    policy_engine_version: str = ""
    validator_version: str = ""
    llm: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "portfolio_id": self.portfolio_id,
            "policy_version": int(self.policy_version),
            "generated_at": self.generated_at,
            "overall_status": self.overall_status,
            "profile_id": self.profile_id,
            "violations": [v.to_dict() for v in self.violations],
            "warnings": list(self.warnings),
            "passed_constraints": [c.to_dict() for c in self.passed_constraints],
            "failed_constraints": [c.to_dict() for c in self.failed_constraints],
            "nearing_limits": [c.to_dict() for c in self.nearing_limits],
            "required_actions": list(self.required_actions),
            "mandate": dict(self.mandate or {}),
            "compliance_score": int(self.compliance_score),
            "diagnostics": dict(self.diagnostics or {}),
            "lineage": list(self.lineage),
            "portfolio_graph_id": self.portfolio_graph_id,
            "portfolio_risk_id": self.portfolio_risk_id,
            "policy_engine_version": self.policy_engine_version,
            "validator_version": self.validator_version,
            "llm": False,
            "violation_count": len(self.violations),
            "passed_count": len(self.passed_constraints),
            "failed_count": len(self.failed_constraints),
        }

    @property
    def is_compliant(self) -> bool:
        return self.overall_status == "Compliant"

    @property
    def has_breach(self) -> bool:
        return self.overall_status in {"Breach", "Critical Breach"}
