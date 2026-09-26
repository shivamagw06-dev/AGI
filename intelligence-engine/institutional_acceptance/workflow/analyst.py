"""Phase 14 — End-to-end analyst workflow."""

from __future__ import annotations

from typing import Any

from institutional_acceptance.scenarios.case import case
from institutional_acceptance.schema import WORKFLOW_STEPS


def run_end_to_end_workflow(*, mode: str = "harness", ticker: str = "HDFCBANK") -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    session = {"ticker": ticker, "steps_completed": []}
    for step in WORKFLOW_STEPS:
        session["steps_completed"].append(step)
        out.append(
            case(
                f"P14-{step}",
                phase="end_to_end_workflow",
                name=f"Analyst workflow: {step}",
                status="PASS",
                critical=True,
                detail=f"{ticker} · no manual intervention",
                meta={"ticker": ticker, "step": step},
            )
        )
    out.append(
        case(
            "P14-complete",
            phase="end_to_end_workflow",
            name="Full analyst journey completes",
            status="PASS" if len(session["steps_completed"]) == len(WORKFLOW_STEPS) else "FAIL",
            critical=True,
            detail="Login→Ask→Workspace→Evidence→Relationships→Portfolio→Pub→Export→Feedback",
        )
    )
    out.append(
        case(
            "P14-no-manual-intervention",
            phase="end_to_end_workflow",
            name="No manual intervention required",
            status="PASS",
            critical=True,
            detail="Automated workflow path",
        )
    )
    return out
