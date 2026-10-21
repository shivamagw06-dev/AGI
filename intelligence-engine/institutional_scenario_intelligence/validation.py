"""Scenario validation — evidence required; no recommendations or prices."""

from __future__ import annotations

import re
from typing import Any

from institutional_scenario_intelligence.schema import InstitutionalScenario, ScenarioReport

_FORBIDDEN = re.compile(
    r"\b(buy|sell|hold|accumulate|reduce|target price|price target|will hit|price will be)\b",
    re.I,
)


def validate_scenario(scenario: InstitutionalScenario) -> list[str]:
    errors: list[str] = []
    if not scenario.narrative:
        errors.append("narrative_required")
    if not scenario.supporting_evidence:
        errors.append("supporting_evidence_required")
    if scenario.probability is not None:
        errors.append("probability_forbidden_until_pci")
    if scenario.is_recommendation or scenario.is_price_prediction:
        errors.append("recommendation_or_price_prediction_forbidden")
    blob = " ".join(scenario.narrative) + " " + str(scenario.drivers.model_dump())
    if _FORBIDDEN.search(blob):
        errors.append("forbidden_recommendation_language")
    return errors


def validate_report(report: ScenarioReport) -> list[str]:
    errors: list[str] = []
    types = {s.type.value for s in report.scenarios}
    for required in ("Bull", "Base", "Bear"):
        if required not in types:
            errors.append(f"missing_{required.lower()}_scenario")
    for s in report.scenarios:
        errors.extend(validate_scenario(s))
    if report.assigns_probabilities or report.is_recommendation or report.is_price_prediction:
        errors.append("report_judgment_flags_invalid")
    blob = str(report.model_dump())
    if _FORBIDDEN.search(blob):
        errors.append("forbidden_language_in_report")
    return errors


def assert_publishable(report: ScenarioReport) -> ScenarioReport:
    errors = validate_report(report)
    if errors:
        raise ValueError(f"scenario_validation_failed: {errors}")
    return report
