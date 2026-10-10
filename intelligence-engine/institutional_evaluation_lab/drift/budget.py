"""Drift budget — release fails when thresholds are breached."""

from __future__ import annotations

from typing import Any

from institutional_evaluation_lab.drift.schema import DRIFT_BUDGET


def evaluate_budget(
    *,
    n: int,
    recommendation_changes: int,
    unknown_count: int,
    governance_failures: int,
    prev_avg_runtime_ms: float | None,
    cur_avg_runtime_ms: float | None,
    prev_avg_readiness: float | None,
    cur_avg_readiness: float | None,
    data_driven_readiness_shift: bool = False,
    budget: dict[str, Any] | None = None,
) -> dict[str, Any]:
    b = {**DRIFT_BUDGET, **(budget or {})}
    denom = max(1, n)
    change_pct = round(100.0 * recommendation_changes / denom, 2)
    unknown_pct = round(100.0 * unknown_count / denom, 2)

    runtime_reg_pct = None
    if prev_avg_runtime_ms and cur_avg_runtime_ms and prev_avg_runtime_ms > 0:
        runtime_reg_pct = round(
            100.0 * (cur_avg_runtime_ms - prev_avg_runtime_ms) / prev_avg_runtime_ms, 2
        )

    readiness_delta_pp = None
    if prev_avg_readiness is not None and cur_avg_readiness is not None:
        # readiness stored as 0–100 or 0–1
        prev_r = prev_avg_readiness * 100 if prev_avg_readiness <= 1.5 else prev_avg_readiness
        cur_r = cur_avg_readiness * 100 if cur_avg_readiness <= 1.5 else cur_avg_readiness
        readiness_delta_pp = round(abs(cur_r - prev_r), 2)

    breaches: list[dict[str, Any]] = []

    if change_pct > float(b["recommendation_change_pct_max"]):
        breaches.append(
            {
                "metric": "recommendation_changes",
                "value": change_pct,
                "threshold": b["recommendation_change_pct_max"],
                "unit": "pct",
            }
        )
    if unknown_pct > float(b["unknown_drift_pct_max"]):
        breaches.append(
            {
                "metric": "unknown_drift",
                "value": unknown_pct,
                "threshold": b["unknown_drift_pct_max"],
                "unit": "pct",
            }
        )
    if governance_failures > int(b["governance_failures_max"]):
        breaches.append(
            {
                "metric": "governance_failures",
                "value": governance_failures,
                "threshold": b["governance_failures_max"],
                "unit": "count",
            }
        )
    if runtime_reg_pct is not None and runtime_reg_pct > float(b["runtime_regression_pct_max"]):
        breaches.append(
            {
                "metric": "runtime_regression",
                "value": runtime_reg_pct,
                "threshold": b["runtime_regression_pct_max"],
                "unit": "pct",
            }
        )
    if (
        readiness_delta_pp is not None
        and readiness_delta_pp > float(b["average_readiness_change_pct_max"])
        and not data_driven_readiness_shift
    ):
        breaches.append(
            {
                "metric": "average_readiness_change",
                "value": readiness_delta_pp,
                "threshold": b["average_readiness_change_pct_max"],
                "unit": "pp",
                "note": "Allowed only when DATA explains the shift",
            }
        )

    return {
        "budget": b,
        "observed": {
            "recommendation_change_pct": change_pct,
            "unknown_drift_pct": unknown_pct,
            "governance_failures": governance_failures,
            "runtime_regression_pct": runtime_reg_pct,
            "average_readiness_change_pp": readiness_delta_pp,
        },
        "breaches": breaches,
        "passed": len(breaches) == 0,
    }
