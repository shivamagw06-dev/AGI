"""Single governed financial-institution valuation entry point."""
from __future__ import annotations
from typing import Any

from financials_valuation.classification import classify_financial_subsector
from financials_valuation.nonbank_service import evaluate_financial_subsector
from financials_valuation.service import evaluate_bank


def evaluate_financial_institution(*, company: dict[str, Any], inputs: dict[str, Any], as_of: str,
                                   peers: list[dict[str, Any]] | None = None,
                                   history: list[dict[str, Any]] | None = None,
                                   scenarios: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    classification = classify_financial_subsector(company)
    if classification.get("subsector") == "COMMERCIAL_BANK":
        return evaluate_bank(company=company, inputs=inputs, as_of=as_of, peers=peers, history=history, scenarios=scenarios)
    return evaluate_financial_subsector(company=company, inputs=inputs, as_of=as_of,
                                        peers=peers, history=history, scenarios=scenarios)
