"""Coverage detection — every answer tracks what was expected, used and missing."""

from __future__ import annotations

from typing import Any, Optional


def measure_coverage(
    *,
    selected: list[str],
    expected: list[str],
    used: list[str],
    available: Optional[list[str]] = None,
    confidences: Optional[list[float]] = None,
) -> dict[str, Any]:
    used_set = set(used or [])
    expected_set = set(expected or [])
    selected_set = set(selected or [])
    available_set = set(available or selected or [])

    missing_expected = sorted(expected_set - used_set)
    unused_selected = sorted(selected_set - used_set)
    surprise = sorted(used_set - selected_set)

    expected_hit = len(expected_set & used_set)
    coverage_pct = round((expected_hit / len(expected_set)) * 100.0, 1) if expected_set else 100.0
    avg_conf = None
    if confidences:
        avg_conf = round(sum(confidences) / len(confidences), 3)

    return {
        "providers_selected": sorted(selected_set),
        "providers_expected": sorted(expected_set),
        "providers_used": sorted(used_set),
        "providers_available": sorted(available_set),
        "providers_missing": missing_expected,
        "providers_unused": unused_selected,
        "providers_surprise": surprise,
        "coverage_pct": coverage_pct,
        "expected_hit": expected_hit,
        "expected_total": len(expected_set),
        "average_confidence": avg_conf,
        "complete": not missing_expected,
    }
