"""MPC-01 core objects — tenancy/workflow; intelligence remains global."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class InstitutionalExecutionContext:
    """Immutable portfolio context that flows through orchestration — never hidden session state."""

    workspace_id: str
    portfolio_id: str
    client_id: str = ""
    mandate_id: str = ""
    role_id: str = "analyst"
    user_id: str = ""
    policy_profile: str = ""
    permissions: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "portfolio_id": self.portfolio_id,
            "client_id": self.client_id,
            "mandate_id": self.mandate_id,
            "role_id": self.role_id,
            "user_id": self.user_id,
            "policy_profile": self.policy_profile,
            "permissions": list(self.permissions),
            "immutable": True,
            "owns_intelligence": False,
            "intelligence_is_global": True,
        }


@dataclass(frozen=True)
class InstitutionalPortfolioRecord:
    portfolio_id: str
    name: str
    mandate_id: str
    policy_profile: str
    client_ids: tuple[str, ...] = ()
    members: tuple[str, ...] = ()
    status: str = "active"
    diagnostics: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "portfolio_id": self.portfolio_id,
            "name": self.name,
            "mandate_id": self.mandate_id,
            "policy_profile": self.policy_profile,
            "client_ids": list(self.client_ids),
            "members": list(self.members),
            "status": self.status,
            "diagnostics": dict(self.diagnostics or {}),
            "intelligence_is_global": True,
            "references_shared_intelligence": True,
        }


@dataclass(frozen=True)
class InstitutionalClient:
    client_id: str
    client_name: str
    portfolios: tuple[str, ...] = ()
    policy_profile: str = "family_office"
    publication_preferences: tuple[str, ...] = ("WeeklyClientReport", "MonthlyReview")
    distribution_targets: tuple[str, ...] = ("workspace", "export")
    diagnostics: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "client_id": self.client_id,
            "client_name": self.client_name,
            "portfolios": list(self.portfolios),
            "policy_profile": self.policy_profile,
            "publication_preferences": list(self.publication_preferences),
            "distribution_targets": list(self.distribution_targets),
            "diagnostics": dict(self.diagnostics or {}),
            "intelligence_is_global": True,
        }


@dataclass(frozen=True)
class InstitutionalPortfolioWorkspace:
    workspace_id: str
    portfolio_id: str
    mandate: str
    members: tuple[str, ...] = ()
    permissions: tuple[str, ...] = ()
    linked_publications: tuple[str, ...] = ()
    client_id: str = ""
    role_id: str = ""
    policy_profile: str = ""
    execution_context: Optional[InstitutionalExecutionContext] = None
    diagnostics: Optional[dict[str, Any]] = None
    ask_deep_link: str = ""
    research_deep_link: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "portfolio_id": self.portfolio_id,
            "mandate": self.mandate,
            "members": list(self.members),
            "permissions": list(self.permissions),
            "linked_publications": list(self.linked_publications),
            "client_id": self.client_id,
            "role_id": self.role_id,
            "policy_profile": self.policy_profile,
            "execution_context": self.execution_context.to_dict() if self.execution_context else None,
            "diagnostics": dict(self.diagnostics or {}),
            "ask_deep_link": self.ask_deep_link,
            "research_deep_link": self.research_deep_link,
            "owns_intelligence": False,
            "intelligence_is_global": True,
        }


@dataclass
class AuditEvent:
    event_id: str
    kind: str
    detail: str
    actor: str = ""
    created_at: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "kind": self.kind,
            "detail": self.detail,
            "actor": self.actor,
            "created_at": self.created_at,
            "meta": dict(self.meta),
        }
