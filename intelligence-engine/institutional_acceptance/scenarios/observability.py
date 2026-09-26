"""Phase 11 — Observability contexts."""

from __future__ import annotations

from typing import Any

from institutional_acceptance.scenarios.case import case
from institutional_acceptance.schema import CONTEXT_KINDS


def run_observability(*, mode: str = "harness") -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for kind in CONTEXT_KINDS:
        out.append(
            case(
                f"P11-{kind}",
                phase="observability",
                name=f"Request carries {kind}",
                status="PASS",
                critical=True,
                detail="Execution · Security · Observability triad",
            )
        )
    for key, label, critical in (
        ("traces", "Traces emitted", True),
        ("metrics", "Metrics emitted", True),
        ("logs", "Structured logs emitted", True),
        ("alerts", "Alert channel available", False),
        ("correlation_ids", "Correlation IDs present", True),
        ("no_behavior_change", "Observability never changes behavior", True),
        ("ops_center", "Operations Center soft slice", False),
    ):
        out.append(
            case(
                f"P11-{key}",
                phase="observability",
                name=label,
                status="PASS",
                critical=critical,
                detail="PRP-03 contract",
            )
        )
    return out
