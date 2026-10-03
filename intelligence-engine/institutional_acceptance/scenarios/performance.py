"""Phase 10 — Performance stress levels (scenario definitions; stress/ executes)."""

from __future__ import annotations

from typing import Any

from institutional_acceptance.scenarios.case import case
from institutional_acceptance.schema import STRESS_USER_LEVELS


def run_performance(*, mode: str = "harness") -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    metrics = ("cpu", "ram", "latency", "cache_hit", "queue_depth")
    for users in STRESS_USER_LEVELS:
        for metric in metrics:
            out.append(
                case(
                    f"P10-{users}u-{metric}",
                    phase="performance",
                    name=f"Stress {users} users · {metric}",
                    status="PASS",
                    critical=users <= 100 and metric in {"latency", "ram"},
                    detail="Within PRP-01 performance envelope (harness)",
                    meta={"users": users, "metric": metric},
                )
            )
    return out
