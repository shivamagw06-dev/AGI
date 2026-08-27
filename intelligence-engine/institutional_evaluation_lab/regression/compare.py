"""Regression compare — protect against score regressions vs baseline."""

from __future__ import annotations

from typing import Any


def compare_to_baseline(
    current: dict[str, Any],
    baseline: dict[str, Any] | None,
    *,
    max_pass_pct_drop: float = 2.0,
    max_mean_drop: float = 1.5,
) -> dict[str, Any]:
    if not baseline:
        return {
            "status": "no_baseline",
            "regression": False,
            "deltas": {},
            "note": "First run establishes baseline.",
        }
    cur_pass = float(current.get("pass_pct") or 0)
    base_pass = float(baseline.get("pass_pct") or 0)
    cur_mean = float(current.get("mean_score") or 0)
    base_mean = float(baseline.get("mean_score") or 0)
    d_pass = round(cur_pass - base_pass, 2)
    d_mean = round(cur_mean - base_mean, 2)
    regression = (d_pass < -max_pass_pct_drop) or (d_mean < -max_mean_drop)
    return {
        "status": "regression" if regression else "ok",
        "regression": regression,
        "deltas": {
            "pass_pct": d_pass,
            "mean_score": d_mean,
        },
        "baseline": {
            "pass_pct": base_pass,
            "mean_score": base_mean,
            "n": baseline.get("n"),
            "run_id": baseline.get("run_id"),
        },
        "current": {
            "pass_pct": cur_pass,
            "mean_score": cur_mean,
            "n": current.get("n"),
        },
    }
