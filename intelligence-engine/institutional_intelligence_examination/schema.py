"""IIEX — Institutional Intelligence Examination (CIO Investment Committee Assessment).

MODULE_CODE is IIEX to avoid collision with Investment Intelligence Engine (app/iie).
"""

from __future__ import annotations

from typing import Any

IIEX_VERSION = "1.0.0"
PROGRAMME = "AGI Institutional Intelligence Examination"
PROGRAMME_SHORT = "IIEX"
MODULE_CODE = "IIEX"

PRIMARY_PRINCIPLE = (
    "This is a CIO Investment Committee Assessment — not a university paper. "
    "Answers must integrate AGIB intelligence modules into coherent, evidence-backed "
    "investment analysis. AGIB platform only; no direct internet search."
)

PASS_PCT = 90.0
NORMALIZED_TOTAL = 500
NORMALIZED_PASS = 450

# Resources allowed
RESOURCES = (
    "AGIB Intelligence Platform only",
    "No direct internet search",
    "All answers must cite supporting evidence from AGIB knowledge base",
)

NO_IIEX_ACTIONS = (
    "call_external_providers",
    "direct_internet_search",
    "fabricate_evidence",
    "recommend_buy_sell_without_evidence",
    "grade_with_llm",
)

FREEZE_LOCKS: dict[str, Any] = {
    "agi_platform_only": True,
    "no_internet_search": True,
    "soft_wire_only": True,
    "deterministic_scoring": True,
    "no_llm_grading": True,
    "measurement_first": True,
    "evidence_required": True,
}

# Final evaluation dimensions (normalized 500)
EVAL_DIMENSIONS: dict[str, int] = {
    "accuracy": 100,
    "reasoning": 100,
    "evidence": 50,
    "historical_context": 50,
    "relationships": 50,
    "forecasting": 50,
    "research_quality": 50,
    "portfolio_thinking": 50,
    "communication": 50,
}

SECTIONS: tuple[str, ...] = (
    "A_Company",
    "B_Market",
    "C_Macro",
    "D_Sector",
    "E_IPO",
    "F_Relationship",
    "G_Historical",
    "H_Forecast",
    "I_Research",
    "J_CIO_Committee",
)
