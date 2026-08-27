"""Quality gates — parser versions failing any gate cannot be deployed."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.parsing.quality.schema import QUALITY_GATES


def evaluate_gates(metrics: dict[str, Any]) -> dict[str, Any]:
    """Evaluate certification/benchmark metrics against QUALITY_GATES."""
    results = []
    failed = []

    def check(name: str, actual: float | None, *, higher_better: bool = True, max_mode: bool = False) -> None:
        threshold = QUALITY_GATES[name]
        if actual is None:
            ok = False
        elif max_mode:
            ok = float(actual) <= float(threshold)
        else:
            ok = float(actual) >= float(threshold) if higher_better else float(actual) <= float(threshold)
        row = {"gate": name, "threshold": threshold, "actual": actual, "passed": ok}
        results.append(row)
        if not ok:
            failed.append(name)

    check("metric_extraction_accuracy_pct", metrics.get("metric_extraction_accuracy_pct"))
    check("canonical_mapping_accuracy_pct", metrics.get("canonical_mapping_accuracy_pct"))
    check("unknown_metric_rate_pct_max", metrics.get("unknown_metric_rate_pct"), max_mode=True)
    check("hierarchy_preservation_pct", metrics.get("hierarchy_preservation_pct"))
    check("replay_determinism_pct", metrics.get("replay_determinism_pct"))
    check("duplicate_draft_rate_pct_max", metrics.get("duplicate_draft_rate_pct"), max_mode=True)
    check("traceability_pct", metrics.get("traceability_pct"))
    check("benchmark_pass_rate_pct", metrics.get("benchmark_pass_rate_pct"))

    return {
        "passed": not failed,
        "production_eligible": not failed,
        "failed_gates": failed,
        "results": results,
        "thresholds": dict(QUALITY_GATES),
    }
