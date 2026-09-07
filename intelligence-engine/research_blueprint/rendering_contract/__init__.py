"""Rendering contract — owner, inputs, outputs, evidence, min confidence per section."""

from __future__ import annotations

from typing import Any

SECTION_CONTRACTS: dict[str, dict[str, Any]] = {
    "business_quality": {
        "inputs": ["filings", "business_model", "peer_context"],
        "expected_outputs": ["moat_judgement", "quality_score"],
        "evidence_requirement": 5,
        "minimum_confidence": 0.8,
    },
    "financial_quality": {
        "inputs": ["financials", "cash_flow", "roic_series"],
        "expected_outputs": ["financial_opinion", "capital_allocation_view"],
        "evidence_requirement": 5,
        "minimum_confidence": 0.8,
    },
    "valuation": {
        "inputs": ["multiples", "history", "peers"],
        "expected_outputs": ["priced_in", "margin_of_safety"],
        "evidence_requirement": 4,
        "minimum_confidence": 0.8,
    },
    "risk": {
        "inputs": ["risk_factors", "balance_sheet", "macro"],
        "expected_outputs": ["risk_map", "severity"],
        "evidence_requirement": 4,
        "minimum_confidence": 0.75,
    },
    "forecast": {
        "inputs": ["historical_earnings", "guidance", "macro"],
        "expected_outputs": ["base_path", "sensitivities"],
        "evidence_requirement": 3,
        "minimum_confidence": 0.7,
    },
    "portfolio_fit": {
        "inputs": ["holdings", "constraints", "risk_budget"],
        "expected_outputs": ["fit_judgement", "sizing_guidance"],
        "evidence_requirement": 2,
        "minimum_confidence": 0.75,
    },
    "committee_opinion": {
        "inputs": ["analyst_opinions", "weights"],
        "expected_outputs": ["vote", "dissent"],
        "evidence_requirement": 3,
        "minimum_confidence": 0.8,
    },
    "cio_summary": {
        "inputs": ["all_section_outputs"],
        "expected_outputs": ["decision_summary"],
        "evidence_requirement": 1,
        "minimum_confidence": 0.85,
    },
    "definition": {
        "inputs": ["concept_lexicon"],
        "expected_outputs": ["plain_definition"],
        "evidence_requirement": 1,
        "minimum_confidence": 0.9,
    },
}


def build_rendering_contract(
    *,
    section_order: list[str],
    section_owner: dict[str, str],
    priorities: dict[str, str],
    quality_rules: dict[str, Any],
) -> dict[str, Any]:
    contracts = []
    for key in section_order:
        if priorities.get(key) in {"suppressed"}:
            continue
        base = SECTION_CONTRACTS.get(
            key,
            {
                "inputs": ["prior_sections", "evidence_pack"],
                "expected_outputs": ["section_judgement"],
                "evidence_requirement": 2,
                "minimum_confidence": 0.75,
            },
        )
        contracts.append(
            {
                "section_key": key,
                "owner": section_owner.get(key),
                "priority": priorities.get(key),
                "inputs": list(base["inputs"]),
                "expected_outputs": list(base["expected_outputs"]),
                "evidence_requirement": base["evidence_requirement"],
                "minimum_confidence": base["minimum_confidence"],
                "render": priorities.get(key) != "hidden",
            }
        )
    return {
        "sections": contracts,
        "global_style": quality_rules.get("writing_style"),
        "citation_rules": quality_rules.get("citation_rules"),
        "max_length_words": quality_rules.get("maximum_length_words"),
    }
