"""Knowledge KPIs — product metrics for universe coverage."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from institutional_knowledge_factory.maturity import calculate_maturity
from institutional_knowledge_factory.quality import compute_knowledge_quality


def _avg(values: list[float]) -> float:
    return round(sum(values) / len(values), 1) if values else 0.0


def calculate_knowledge_kpis(
    ikos: list[dict[str, Any]],
    *,
    universe: str = "NIFTY_50",
) -> dict[str, Any]:
    """Aggregate knowledge KPIs for a compiled universe."""
    if not ikos:
        return {
            "universe": universe,
            "compiled": 0,
            "compiled_pct": 0,
            "status": "empty",
        }

    supported_counts: list[float] = []
    unknown_counts: list[float] = []
    contradiction_counts: list[float] = []
    evidence_coverage: list[float] = []
    stale_counts: list[float] = []
    grades: list[str] = []

    for iko in ikos:
        claims = iko.get("claims") or []
        quality = compute_knowledge_quality(iko)
        maturity = calculate_maturity(iko)
        metrics = quality.get("metrics") or {}

        supported_counts.append(sum(1 for c in claims if str(c.get("state")) == "SUPPORTED"))
        unknown_counts.append(metrics.get("unknown_count", 0))
        contradiction_counts.append(metrics.get("contradiction_count", 0))
        evidence_coverage.append(metrics.get("evidence_coverage", 0))
        stale_counts.append(sum(1 for c in claims if str(c.get("state")) == "STALE"))
        grades.append(maturity.get("institutional_grade", "C"))

    # Grade distribution → headline grade (mode of top half)
    grade_order = {"A": 7, "A-": 6, "B+": 5, "B": 4, "B-": 3, "C+": 2, "C": 1}
    sorted_grades = sorted(grades, key=lambda g: grade_order.get(g, 0), reverse=True)
    headline_grade = sorted_grades[len(sorted_grades) // 2] if sorted_grades else "C"

    return {
        "universe": universe,
        "compiled": len(ikos),
        "knowledge_grade": headline_grade,
        "average_supported_assertions": _avg(supported_counts),
        "average_unknowns": _avg(unknown_counts),
        "average_contradictions": _avg(contradiction_counts),
        "evidence_coverage_pct": _avg(evidence_coverage),
        "stale_assertions_pct": round(
            100.0 * sum(stale_counts) / max(sum(len(i.get("claims") or []) for i in ikos), 1),
            1,
        ),
        "last_refresh": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "status": "ok",
    }
