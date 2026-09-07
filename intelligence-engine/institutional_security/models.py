"""PRP-02 core security objects — complement InstitutionalExecutionContext."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class InstitutionalSecurityContext:
    """Identity + authorization context. Never mutates intelligence."""

    user_id: str
    tenant_id: str
    role: str
    permissions: tuple[str, ...] = ()
    authentication_method: str = "password"
    api_key_id: str = ""
    session_id: str = ""
    correlation_id: str = ""
    diagnostics: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "role": self.role,
            "permissions": list(self.permissions),
            "authentication_method": self.authentication_method,
            "api_key_id": self.api_key_id or None,
            "session_id": self.session_id or None,
            "correlation_id": self.correlation_id or None,
            "diagnostics": dict(self.diagnostics or {}),
            "immutable": True,
            "enters_intelligence_layer": False,
            "complements_execution_context": True,
        }

    def has(self, permission: str) -> bool:
        return permission in set(self.permissions)


@dataclass(frozen=True)
class InstitutionalAuditEvent:
    """Immutable, append-only audit record. References IDs; does not duplicate objects."""

    event_id: str
    timestamp: str
    user_id: str
    tenant_id: str
    action: str
    resource: str
    resource_id: str = ""
    outcome: str = "success"
    correlation_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "action": self.action,
            "resource": self.resource,
            "resource_id": self.resource_id,
            "outcome": self.outcome,
            "correlation_id": self.correlation_id,
            "metadata": dict(self.metadata or {}),
            "immutable": True,
            "append_only": True,
        }


@dataclass(frozen=True)
class InstitutionalTenant:
    tenant_id: str
    name: str
    status: str = "active"
    user_ids: tuple[str, ...] = ()
    client_ids: tuple[str, ...] = ()
    portfolio_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "name": self.name,
            "status": self.status,
            "user_ids": list(self.user_ids),
            "client_ids": list(self.client_ids),
            "portfolio_ids": list(self.portfolio_ids),
            "intelligence_is_global": True,
            "tenant_data_isolated": True,
        }
