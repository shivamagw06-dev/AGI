"""IB-01 scoring sections A–H."""

from __future__ import annotations

from institutional_grade_benchmark.sections.analyst_productivity import score_analyst_productivity
from institutional_grade_benchmark.sections.blind_comparison import score_blind_comparison
from institutional_grade_benchmark.sections.company_research import score_company_research
from institutional_grade_benchmark.sections.explainability import score_explainability
from institutional_grade_benchmark.sections.hallucination import score_hallucination
from institutional_grade_benchmark.sections.portfolio import score_portfolio
from institutional_grade_benchmark.sections.speed import score_speed
from institutional_grade_benchmark.sections.stress_reasoning import score_stress_reasoning

SECTION_SCORERS = {
    "company_research": score_company_research,
    "blind_comparison": score_blind_comparison,
    "hallucination": score_hallucination,
    "speed": score_speed,
    "portfolio": score_portfolio,
    "explainability": score_explainability,
    "analyst_productivity": score_analyst_productivity,
    "stress_reasoning": score_stress_reasoning,
}

__all__ = ["SECTION_SCORERS"]
