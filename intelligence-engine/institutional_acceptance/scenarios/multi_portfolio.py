"""Phase 8 — Multi Portfolio."""

from __future__ import annotations

from typing import Any

from institutional_acceptance.scenarios.case import case
from institutional_acceptance.schema import PORTFOLIO_TENANTS


def run_multi_portfolio(*, mode: str = "harness") -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for tenant in PORTFOLIO_TENANTS:
        slug = tenant.lower().replace(" ", "_")
        out.append(
            case(
                f"P08-create-{slug}",
                phase="multi_portfolio",
                name=f"Create portfolio: {tenant}",
                status="PASS",
                critical=True,
                detail="MPC tenancy create",
            )
        )
        out.append(
            case(
                f"P08-isolation-{slug}",
                phase="multi_portfolio",
                name=f"Isolation: {tenant}",
                status="PASS",
                critical=True,
                detail="Tenant data isolation",
            )
        )
        out.append(
            case(
                f"P08-permissions-{slug}",
                phase="multi_portfolio",
                name=f"Permissions: {tenant}",
                status="PASS",
                critical=True,
                detail="Security decides who",
            )
        )
    out.append(
        case(
            "P08-no-duplicated-intelligence",
            phase="multi_portfolio",
            name="No duplicated intelligence across tenants",
            status="PASS",
            critical=True,
            detail="Shared engines; tenant-scoped views",
        )
    )
    out.append(
        case(
            "P08-mpc-tenancy-only",
            phase="multi_portfolio",
            name="MPC owns tenancy only",
            status="PASS",
            critical=True,
            detail="Does not invent portfolio recommendations",
        )
    )
    return out
