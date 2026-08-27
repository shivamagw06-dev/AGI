"""PCC quality gates — failing any gate blocks production eligibility."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.parsing.pcc.schema import PCC_GATES


def evaluate_pcc_gates(metrics: dict[str, Any]) -> dict[str, Any]:
    results = []
    failed = []

    def check(name: str, actual: float | None, *, max_mode: bool = False) -> None:
        threshold = PCC_GATES[name]
        if actual is None:
            ok = False
        elif max_mode:
            ok = float(actual) <= float(threshold)
        else:
            ok = float(actual) >= float(threshold)
        row = {"gate": name, "threshold": threshold, "actual": actual, "passed": ok}
        results.append(row)
        if not ok:
            failed.append(name)

    check("parse_manifest_match_pct", metrics.get("parse_manifest_match_pct"))
    check("coverage_matrix_match_pct", metrics.get("coverage_matrix_match_pct"))
    check("hierarchy_preservation_pct", metrics.get("hierarchy_preservation_pct"))
    check("metric_mapping_accuracy_pct", metrics.get("metric_mapping_accuracy_pct"))
    check("unknown_label_rate_pct_max", metrics.get("unknown_label_rate_pct"), max_mode=True)
    check("validation_consistency_pct", metrics.get("validation_consistency_pct"))
    check("replay_determinism_pct", metrics.get("replay_determinism_pct"))
    check("regression_detection_pct", metrics.get("regression_detection_pct"))

    certification_pass = not failed and bool(metrics.get("all_cases_passed", False))
    if not certification_pass and "certification_pass" not in failed:
        # explicit required gate
        results.append(
            {
                "gate": "certification_pass",
                "threshold": True,
                "actual": bool(metrics.get("all_cases_passed")),
                "passed": certification_pass,
            }
        )
        if not certification_pass:
            failed.append("certification_pass")

    return {
        "passed": not failed,
        "production_eligible": not failed,
        "deployment_recommendation": "deploy" if not failed else "block_deployment",
        "failed_gates": failed,
        "results": results,
        "thresholds": dict(PCC_GATES),
    }
