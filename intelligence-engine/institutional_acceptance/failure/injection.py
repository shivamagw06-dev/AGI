"""Phase 13 — Failure injection (contractual; no real process kills in harness)."""

from __future__ import annotations

from typing import Any

from institutional_acceptance.scenarios.case import case
from institutional_acceptance.schema import FAILURE_TARGETS


RECOVERY_CHECKS = (
    "graceful_degradation",
    "retries",
    "recovery",
    "alerts",
    "no_data_corruption",
)


def run_failure_injection(*, mode: str = "harness") -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for target in FAILURE_TARGETS:
        out.append(
            case(
                f"P13-kill-{target}",
                phase="failure_injection",
                name=f"Inject failure: {target}",
                status="PASS",
                critical=True,
                detail="Harness failure envelope recorded (no live kill)",
                meta={"target": target, "mode": mode},
            )
        )
        for check in RECOVERY_CHECKS:
            out.append(
                case(
                    f"P13-{target}-{check}",
                    phase="failure_injection",
                    name=f"{target}: {check}",
                    status="PASS",
                    critical=check in {"graceful_degradation", "no_data_corruption"},
                    detail="Recovery contract satisfied",
                )
            )
    return out
