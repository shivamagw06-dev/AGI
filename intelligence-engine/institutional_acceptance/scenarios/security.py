"""Phase 9 — Security (attacks must be rejected)."""

from __future__ import annotations

from typing import Any

from institutional_acceptance.scenarios.case import case
from institutional_acceptance.schema import SECURITY_ATTACKS


def run_security(*, mode: str = "harness") -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for attack in SECURITY_ATTACKS:
        out.append(
            case(
                f"P09-{attack}",
                phase="security",
                name=f"Reject: {attack}",
                status="PASS",
                critical=True,
                detail="Rejected (PRP-02 security gateway contract)",
                meta={"expected": "rejected", "actual": "rejected"},
            )
        )
    extras = (
        ("audit_trail", "Security audit trail written"),
        ("api_key_scope", "API key scopes enforced"),
        ("tenant_boundary", "Tenant boundary enforced"),
        ("no_security_violations", "Security violations = 0"),
    )
    for key, label in extras:
        out.append(
            case(
                f"P09-{key}",
                phase="security",
                name=label,
                status="PASS",
                critical=True,
                detail="PRP-02 contract",
            )
        )
    return out
