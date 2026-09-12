"""Accuracy engine — analyst / committee / forecast / portfolio / scenario / evidence."""

from __future__ import annotations

from typing import Any

from institutional_memory.analyst_memory.engine import analyst_history
from institutional_memory.committee_memory.engine import committee_history
from institutional_memory.forecast_memory.engine import forecast_history
from institutional_memory.portfolio_memory.engine import portfolio_history
from institutional_memory.store.corpus import get_company


def accuracy_dashboard(ticker: str, *, portfolio_id: str = "agib_core_india") -> dict[str, Any]:
    company = get_company(ticker)
    if not company:
        return {"found": False, "ticker": (ticker or "").upper()}
    analysts = analyst_history(ticker)
    committee = committee_history(ticker)
    forecasts = forecast_history(ticker)
    portfolio = portfolio_history(portfolio_id)
    evidence_rows = company.get("evidence_history") or []
    evidence_accuracy = 0.7 + 0.05 * sum(1 for e in evidence_rows if e.get("retained"))
    evidence_accuracy = min(0.95, round(evidence_accuracy, 3))
    scenario_accuracy = forecasts.get("mean_calibration")
    return {
        "found": True,
        "ticker": company["ticker"],
        "analyst_accuracy": analysts.get("mean_accuracy"),
        "committee_accuracy": committee.get("consensus_accuracy"),
        "forecast_accuracy": forecasts.get("mean_calibration"),
        "scenario_accuracy": scenario_accuracy,
        "portfolio_accuracy": portfolio.get("success_rate"),
        "evidence_accuracy": evidence_accuracy,
        "continuously_updated": True,
        "components": {
            "analyst": analysts.get("historical_evolution"),
            "committee": committee.get("evolution"),
            "forecast": forecasts.get("history"),
        },
        "rule": "Accuracy continuously updated as outcomes arrive",
    }
