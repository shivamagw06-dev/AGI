"""100-point rubric, critical failures and reusable root-cause labels."""

from __future__ import annotations

from typing import Any

from agi_improvement_engine.schema import CRITICAL_FAILURES, FAILURE_TAXONOMY, SCORE_WEIGHTS


def score_evaluation(evaluation: dict[str, Any]) -> dict[str, Any]:
    dimensions = evaluation.get("dimensions") or {}
    scored: dict[str, float] = {}
    for name, weight in SCORE_WEIGHTS.items():
        raw = float(dimensions.get(name, 0))
        scored[name] = round(max(0.0, min(raw, 100.0)) * weight / 100.0, 2)
    critical = sorted({str(x) for x in evaluation.get("critical_failures") or [] if str(x) in CRITICAL_FAILURES})
    causes = sorted({str(x) for x in evaluation.get("root_causes") or [] if str(x) in FAILURE_TAXONOMY})
    total = round(sum(scored.values()), 2)
    passed = total >= 70.0 and not critical
    return {
        "score": 0.0 if critical else total,
        "pre_critical_score": total,
        "passed": passed,
        "critical_failure": bool(critical),
        "critical_failures": critical,
        "root_causes": causes,
        "weighted_dimensions": scored,
        "notes": str(evaluation.get("notes") or "")[:2000],
    }
