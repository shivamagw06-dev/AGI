"""IRS release / merge gate — final quality gate before production."""

from __future__ import annotations

from typing import Any

from academy.regression.schema import REGRESSION_EPSILON


def evaluate_gate(
    *,
    benchmark: dict[str, Any],
    delta: dict[str, Any],
    certification: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge blocked if intelligence regresses or critical quality fails."""
    reasons: list[str] = []
    iq = delta.get("overall_institutional_iq") or {}
    iq_delta = float(iq.get("delta") or 0.0)
    if iq_delta < -REGRESSION_EPSILON:
        reasons.append(f"Overall IQ decreased ({iq_delta})")

    analysts = delta.get("analysts") or {}
    for key in ("business", "financial", "valuation"):
        d = float((analysts.get(key) or {}).get("delta") or 0.0)
        if d < -REGRESSION_EPSILON:
            reasons.append(f"{key} reasoning decreased ({d})")

    hall = benchmark.get("hallucinations") or {}
    if int(hall.get("critical_count") or 0) > 0:
        reasons.append("Critical hallucinations present")
    # Block if critical increased vs previous
    hall_delta = delta.get("hallucinations") or {}
    if int(hall_delta.get("current_critical") or 0) > int(hall_delta.get("previous_critical") or 0):
        reasons.append("Critical hallucinations increased")

    drift = benchmark.get("analyst_drift") or {}
    drift_delta = delta.get("analyst_drift") or {}
    if int(drift.get("total") or 0) > 0 and int(drift_delta.get("current") or 0) > int(drift_delta.get("previous") or 0):
        reasons.append("Analyst drift increased")
    if int(drift.get("total") or 0) > 3:
        reasons.append("Analyst drift above threshold")

    cert_status = (certification or {}).get("status") or (certification or {}).get("certified")
    cert_pass = cert_status in {True, "PASS", "pass", "certified"}
    if certification is not None and not cert_pass:
        reasons.append("Certification failed")

    # Recommendation policy: critical/high recommendation_policy findings
    policy_fail = False
    for f in hall.get("findings") or []:
        if f.get("category") == "recommendation_policy" and f.get("severity") in {"critical", "high"}:
            policy_fail = True
            break
    if policy_fail:
        reasons.append("Recommendation policy violated")

    # Golden benchmark floor
    overall = float(benchmark.get("overall_institutional_iq") or 0.0)
    if overall < 70.0:
        reasons.append("Golden benchmark overall IQ below 70")

    regression_pass = iq_delta >= -REGRESSION_EPSILON and overall >= 70.0
    allow = len(reasons) == 0
    return {
        "allow_merge": allow,
        "merge_status": "APPROVED" if allow else "BLOCKED",
        "regression_pass": regression_pass,
        "recommendation_policy_pass": not policy_fail,
        "certification_pass": cert_pass if certification is not None else True,
        "reasons": reasons,
        "epsilon": REGRESSION_EPSILON,
        "primary_question": "Did this pull request make AGIB smarter?",
        "answer": (
            "Yes — intelligence maintained or improved"
            if allow and iq_delta >= 0
            else ("No regression detected" if allow else "No — merge blocked")
        ),
    }
