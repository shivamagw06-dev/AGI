"""Deterministic expected-vs-actual comparison rules."""

from __future__ import annotations

from typing import Any

from forecast_validation_learning.schema import (
    ActualOutcome,
    ExpectedOutcome,
    OutcomeDifference,
    ValidationStatus,
)

_ORDER = {"Bear": 0, "Base": 1, "Bull": 2, "Unknown": 1}


def _scenario_distance(expected: str, actual: str) -> int:
    if actual == "Unknown" or expected not in _ORDER or actual not in _ORDER:
        return 1
    return abs(_ORDER[expected] - _ORDER[actual])


def compare_outcomes(expected: ExpectedOutcome, actual: ActualOutcome) -> OutcomeDifference:
    dist = _scenario_distance(expected.modal_scenario, actual.realized_scenario)
    scenario_match = dist == 0 and actual.realized_scenario != "Unknown"

    growth_match = expected.growth_direction == actual.growth_direction
    margin_match = expected.margin_direction == actual.margin_direction

    cat_expected = [c.lower() for c in expected.catalysts]
    cat_actual = [c.lower() for c in actual.catalysts_materialized]
    hits = 0
    if cat_expected:
        for e in cat_expected:
            if any(e in a or a in e or _token_overlap(e, a) for a in cat_actual):
                hits += 1
        catalyst_hit_rate = hits / len(cat_expected)
    else:
        catalyst_hit_rate = 0.5 if cat_actual else 0.0

    timing_match = False
    if expected.timing_horizon == "near":
        timing_match = actual.timing_realized in {"early", "on_time"}
    elif expected.timing_horizon == "long":
        timing_match = actual.timing_realized in {"on_time", "late"}
    else:
        timing_match = actual.timing_realized in {"on_time", "early"}

    checks = [scenario_match, growth_match, margin_match, timing_match, catalyst_hit_rate >= 0.34]
    agreement = 100.0 * (sum(1 for c in checks if c) / len(checks))

    summary_parts = []
    if scenario_match:
        summary_parts.append(f"Modal scenario {expected.modal_scenario} realized")
    else:
        summary_parts.append(
            f"Expected {expected.modal_scenario}, realized {actual.realized_scenario}"
        )
    if not growth_match:
        summary_parts.append(
            f"growth {expected.growth_direction}→{actual.growth_direction}"
        )
    if not margin_match:
        summary_parts.append(
            f"margins {expected.margin_direction}→{actual.margin_direction}"
        )
    summary_parts.append(f"catalyst hit-rate {catalyst_hit_rate:.0%}")

    return OutcomeDifference(
        scenario_match=scenario_match,
        scenario_distance=dist,
        growth_match=growth_match,
        margin_match=margin_match,
        catalyst_hit_rate=round(catalyst_hit_rate, 4),
        timing_match=timing_match,
        metric_agreement_pct=round(agreement, 2),
        summary="; ".join(summary_parts),
        details={
            "checks": {
                "scenario": scenario_match,
                "growth": growth_match,
                "margin": margin_match,
                "timing": timing_match,
                "catalysts": catalyst_hit_rate >= 0.34,
            },
            "catalyst_hits": hits if cat_expected else 0,
            "catalysts_expected": len(cat_expected),
        },
    )


def decide_status(
    difference: OutcomeDifference,
    *,
    actual: ActualOutcome,
) -> ValidationStatus:
    if actual.realized_scenario == "Unknown" or not actual.evidence:
        return "Indeterminate"

    agr = difference.metric_agreement_pct
    if difference.scenario_match and agr >= 70:
        return "Validated"
    if difference.scenario_distance <= 1 and agr >= 40:
        return "Partially Correct"
    if agr < 40 or difference.scenario_distance >= 2:
        return "Incorrect"
    return "Partially Correct"


def _token_overlap(a: str, b: str) -> bool:
    ta = {t for t in a.replace("/", " ").split() if len(t) > 3}
    tb = {t for t in b.replace("/", " ").split() if len(t) > 3}
    return bool(ta & tb)


def validation_confidence(difference: OutcomeDifference, actual: ActualOutcome) -> int:
    base = 55
    if actual.evidence:
        base += min(25, 5 * len(actual.evidence))
    if difference.scenario_match:
        base += 10
    if difference.catalyst_hit_rate >= 0.5:
        base += 5
    if actual.realized_scenario == "Unknown":
        base = 35
    return max(30, min(97, base))
