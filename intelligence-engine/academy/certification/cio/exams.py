"""CIO certification exams — Level 14 coherence."""

from __future__ import annotations

from academy.certification.benchmark_suite.companies import BENCHMARK_COMPANIES
from academy.certification.schema import ExamSpec


def exams() -> list[ExamSpec]:
    out: list[ExamSpec] = []
    for i, co in enumerate(BENCHMARK_COMPANIES[:10]):
        out.append(
            ExamSpec(
                exam_id=f"acs_cio_{i+1:03d}",
                level=14,
                analyst="cio",
                question=(
                    f"As CIO, combine nine analysts + committee + research writer into one coherent "
                    f"investment report on {co['name']} without changing facts, confidence or odds."
                ),
                company=co["name"],
                ticker=co["ticker"],
                topic="CIO Coherence",
                must_include=["cio", "committee", "analyst", "coherent", "report"],
                tags=["cio"],
            )
        )
    return out
