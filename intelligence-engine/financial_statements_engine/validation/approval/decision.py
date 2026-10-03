"""Deterministic approval state machine."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.validation.schema import APPROVAL_STATES, BLOCK_ON_ERROR


def decide(
    findings: list[dict[str, Any]],
    *,
    quality: dict[str, Any] | None = None,
    block_on_error: bool | None = None,
) -> dict[str, Any]:
    block_err = BLOCK_ON_ERROR if block_on_error is None else block_on_error
    critical = [f for f in findings if f.get("status") == "FAIL" and f.get("severity") == "CRITICAL"]
    errors = [f for f in findings if f.get("status") == "FAIL" and f.get("severity") == "ERROR"]
    warnings = [
        f
        for f in findings
        if f.get("severity") == "WARNING" and f.get("status") in ("FAIL", "WARN")
    ]

    inp_critical = [f for f in critical if str(f.get("rule_id") or "").startswith("INP_")]

    if inp_critical:
        state = "QUARANTINED"
    elif critical:
        state = "REJECTED"
    elif errors and block_err:
        state = "REJECTED"
    elif warnings or (errors and not block_err):
        state = "APPROVED_WITH_WARNINGS"
    else:
        state = "APPROVED"

    if quality and quality.get("grade") == "Fail" and state in ("APPROVED", "APPROVED_WITH_WARNINGS"):
        # Fail grade only blocks when there were hard failures already reflected;
        # if grade is Fail solely from low score without critical/error, downgrade to REJECTED
        if critical or (errors and block_err) or float(quality.get("score") or 0) < 0.50:
            state = "REJECTED"

    assert state in APPROVAL_STATES
    return {
        "approval_status": state,
        "publishable": state in ("APPROVED", "APPROVED_WITH_WARNINGS"),
        "critical_n": len(critical),
        "error_n": len(errors),
        "warning_n": len(warnings),
        "block_on_error": block_err,
        "deterministic": True,
    }
