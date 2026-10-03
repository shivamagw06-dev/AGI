"""Dynamic Research Blueprint Engine (DRBE) V1 — RQ1 Sprint 8."""

from __future__ import annotations

from typing import Any

DRBE_VERSION = "1.0.0"
PROGRAMME = "RQ1 — Research Ontology"
PROGRAMME_SHORT = "DRBE"
SPRINT = 8
SPRINT_NAME = "Dynamic Research Blueprint Engine (DRBE) V1"
ARCHITECTURE_STATUS = "v1.0.1 LOCKED"
CONFIDENCE_THRESHOLD = 0.85
MAX_BLUEPRINT_MS_TARGET = 20

REPORT_TYPES: tuple[str, ...] = (
    "institutional_investment_report",
    "company_research_report",
    "sector_research_report",
    "industry_report",
    "historical_valuation_report",
    "macro_intelligence_report",
    "portfolio_memorandum",
    "investment_committee_memo",
    "scenario_analysis",
    "stress_test",
    "comparison_report",
    "forecast_report",
    "risk_report",
    "accounting_review",
    "management_review",
    "news_brief",
    "educational_guide",
    "screening_report",
    "market_open_brief",
    "market_close_brief",
)

SECTION_PRIORITIES: tuple[str, ...] = ("mandatory", "optional", "hidden", "suppressed")

MANDATORY_OUTPUT_FIELDS: tuple[str, ...] = (
    "question",
    "report_type",
    "report_name",
    "sections",
    "section_order",
    "section_owner",
    "hidden_sections",
    "optional_sections",
    "mandatory_sections",
    "suppressed_sections",
    "quality_rules",
    "rendering_contract",
    "assignment_book",
)


def constitution_dict() -> dict[str, Any]:
    return {
        "id": "drbe-v1",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": DRBE_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "not_a_top_level_intelligence_layer": True,
        "extends": "Analyst Router / Layer Router / Research Objective",
        "primary_question": "What is the optimal institutional report structure?",
        "law": (
            "The blueprint is finalised before research begins. "
            "Every question deserves a different report — never one universal template."
        ),
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "max_blueprint_ms_target": MAX_BLUEPRINT_MS_TARGET,
        "report_types": list(REPORT_TYPES),
        "research_assignment_book": True,
        "mandatory_output_fields": list(MANDATORY_OUTPUT_FIELDS),
        "success_criteria": {
            "blueprint_accuracy": 0.99,
            "correct_report_selection": 0.99,
            "correct_section_ownership": 1.0,
            "no_irrelevant_sections": 1.0,
            "blueprint_generation_ms": MAX_BLUEPRINT_MS_TARGET,
            "benchmark_minimum": 1000,
        },
    }


DRBE_CONSTITUTION: dict[str, Any] = constitution_dict()
