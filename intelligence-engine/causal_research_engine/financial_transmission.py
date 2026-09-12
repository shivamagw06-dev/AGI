"""Deterministic CRE to AFE bridge."""

from __future__ import annotations

import hashlib
from typing import Any

from financial_engine import calculate
from causal_research_engine.schema import FinancialImpact


def calculate_impact(*, company_id: str, event_id: str, metric: str, calculation_id: str,
                     inputs: dict[str, Any], evidence_ids: tuple[str, ...], analysis_as_of: str,
                     scenario: str | None = None, assumptions: tuple[str, ...] = ()) -> FinancialImpact:
    result = calculate(calculation_id=calculation_id, inputs=inputs, as_of=analysis_as_of,
                       assumptions=[{"text": item} for item in assumptions])
    impact_id = "CRE-IMPACT-" + hashlib.sha256(f"{company_id}|{event_id}|{metric}|{scenario}".encode()).hexdigest()[:16].upper()
    if result.get("status") != "SUCCESS":
        return FinancialImpact(impact_id, company_id, event_id, metric, "UNKNOWN", "HYPOTHESIS",
                               assumptions=assumptions, evidence_ids=evidence_ids, status="QUARANTINED",
                               analysis_as_of=analysis_as_of, afe_result=result)
    value = float(result["calculated_value"])
    return FinancialImpact(impact_id, company_id, event_id, metric,
                           "POSITIVE" if value > 0 else "NEGATIVE" if value < 0 else "MIXED",
                           "SCENARIO" if scenario else "CALCULATION", estimated_change=value,
                           unit=result.get("unit"), period=result.get("period"), scenario=scenario,
                           calculation_id=result.get("calculation_id"), afe_result=result,
                           assumptions=assumptions, evidence_ids=evidence_ids, confidence=.7,
                           analysis_as_of=analysis_as_of)
