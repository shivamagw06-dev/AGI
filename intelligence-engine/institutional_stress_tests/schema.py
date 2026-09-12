"""IST — AGI Institutional Stress Tests (orchestration exams)."""

from __future__ import annotations

from typing import Any

IST_VERSION = "1.0.0"
PROGRAMME = "AGI Institutional Stress Tests"
PROGRAMME_SHORT = "IST"
MODULE_CODE = "IST"
IST01_WORKSTREAM_ID = "IST-01"
IST01_CASE_ID = "IST-01"
IST01_SPEC = "docs/AGI_IST_01_KOTAK_RBI_STRESS_TEST.md"

PASS_SCORE = 70.0  # weighted rubric %
ORCHESTRATION_PASS_RATIO = 1.0  # every required module must contribute

# Modules that MUST contribute — no single module can pass alone
REQUIRED_MODULES: tuple[str, ...] = (
    "FSE",
    "FIL",
    "FIRE-01",
    "FIRE-02",
    "FIRE-03",
    "FIRE-04",
    "FIRE-05",
    "FIRE-06",
    "CIO-01",
    "WO-01",
    "AskAGI",
)

OPTIONAL_MODULES: tuple[str, ...] = (
    "PO-01",
    "CW-01",
    "IO-01",
    "PEB-01",
    "OfficeSDK",
)

# Rubric weights (sum = 100)
RUBRIC_WEIGHTS: dict[str, float] = {
    "financial_reasoning": 15.0,
    "business_reasoning": 15.0,
    "evidence_consistency": 10.0,
    "management_execution": 10.0,
    "comparative_analysis": 10.0,
    "historical_timeline": 10.0,
    "missing_evidence_identification": 10.0,
    "confidence_calibration": 10.0,
    "source_traceability": 10.0,
}

REQUIRED_QUESTIONS: tuple[dict[str, Any], ...] = (
    {"id": "Q1", "title": "What actually happened?", "key": "what_happened"},
    {"id": "Q2", "title": "What caused it?", "key": "what_caused_it"},
    {"id": "Q3", "title": "Were the causes temporary or structural?", "key": "temporary_or_structural"},
    {"id": "Q4", "title": "Did management correctly diagnose the issue?", "key": "management_diagnosis"},
    {"id": "Q5", "title": "Did subsequent execution match management promises?", "key": "execution_vs_promises"},
    {"id": "Q6", "title": "How did financial quality evolve?", "key": "financial_quality_evolution"},
    {"id": "Q7", "title": "How did competitors perform over the same period?", "key": "competitor_performance"},
    {"id": "Q8", "title": "Did Kotak gain or lose relative business quality?", "key": "relative_business_quality"},
    {"id": "Q9", "title": "What evidence contradicts the investment thesis?", "key": "evidence_against"},
    {"id": "Q10", "title": "What evidence supports the investment thesis?", "key": "evidence_supporting"},
    {"id": "Q11", "title": "Which evidence is still missing?", "key": "missing_evidence"},
    {"id": "Q12", "title": "Final Institutional View", "key": "final_institutional_view"},
)

FINAL_VIEW_KEYS: tuple[str, ...] = (
    "investment_thesis",
    "evidence_supporting",
    "evidence_against",
    "remaining_unknowns",
    "confidence",
    "evidence_references",
    "questions_requiring_monitoring",
)

# Automatic failure codes
FAILURE_CODES: tuple[str, ...] = (
    "BUY_WITHOUT_EVIDENCE",
    "SELL_WITHOUT_EVIDENCE",
    "IGNORES_CONTRADICTORY_EVIDENCE",
    "HALLUCINATED_FACTS",
    "UNATTRIBUTED_EXTERNAL_INFO",
    "LOST_PROVENANCE",
    "MIXES_OPINION_WITH_FACT",
    "NO_UNKNOWNS_IDENTIFIED",
    "SINGLE_MODULE_RESPONSE",
    "MISSING_REQUIRED_MODULES",
    "ORCHESTRATION_INCOMPLETE",
    "COLLAPSED_TO_BUY_SELL",
)

NO_IST_ACTIONS = (
    "pass_with_single_module",
    "emit_buy_sell_as_answer",
    "fabricate_evidence",
    "grade_with_llm",
    "skip_contradictory_evidence",
    "skip_unknowns",
)

FREEZE_LOCKS: dict[str, Any] = {
    "orchestration_required": True,
    "no_single_module_pass": True,
    "no_buy_sell_verdict": True,
    "deterministic_scoring": True,
    "no_llm_grading": True,
    "soft_wire_only": True,
    "provenance_required": True,
}
