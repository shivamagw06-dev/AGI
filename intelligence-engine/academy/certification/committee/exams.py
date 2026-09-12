"""Investment Committee certification exams."""

from __future__ import annotations

from academy.certification.benchmark_suite.companies import BENCHMARK_COMPANIES
from academy.certification.schema import ExamSpec


def exams() -> list[ExamSpec]:
    out: list[ExamSpec] = []
    for i, co in enumerate(BENCHMARK_COMPANIES[:15]):
        out.append(
            ExamSpec(
                exam_id=f"acs_ic_{i+1:03d}",
                level=8,
                analyst="committee",
                question=f"Committee memo: should we advance {co['name']}? Synthesise Business→Financial→Valuation→Risk→Committee.",
                company=co["name"],
                ticker=co["ticker"],
                topic="Committee Synthesis",
                must_include=["business", "financial", "valuation", "risk", "committee", "conclusion"],
                tags=["committee", "decision_chain"],
            )
        )
    return out
