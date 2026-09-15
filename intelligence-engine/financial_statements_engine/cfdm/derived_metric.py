"""Derived Metric object — never overwrites reported facts (FSE-03 §16)."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.util import now_iso


def build_derived_metric(
    *,
    company_id: str,
    period_id: str,
    metric: str,
    formula: str,
    dependencies: list[str],
    calculated_value: float | None,
    calculation_version: str,
) -> dict[str, Any]:
    return {
        "company_id": company_id,
        "period_id": period_id,
        "metric": metric,
        "formula": formula,
        "dependencies": list(dependencies),
        "calculated_value": calculated_value,
        "calculation_version": calculation_version,
        "calculation_timestamp": now_iso(),
        "derived": True,
        "overwrites_reported": False,
        "object": "derived_metric",
    }
