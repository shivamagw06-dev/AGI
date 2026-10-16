"""Portfolio thinking certification exams — Level 11."""

from __future__ import annotations

from academy.certification.benchmark_suite.companies import BENCHMARK_COMPANIES
from academy.certification.schema import ExamSpec


def exams() -> list[ExamSpec]:
    out: list[ExamSpec] = []
    for i, co in enumerate(BENCHMARK_COMPANIES[:15]):
        out.append(
            ExamSpec(
                exam_id=f"acs_port_{i+1:03d}",
                level=11,
                analyst="portfolio",
                question=(
                    f"Should {co['name']} improve THIS portfolio? Consider diversification, factor exposure, "
                    f"sector concentration, risk, expected return, drawdown and correlation."
                ),
                company=co["name"],
                ticker=co["ticker"],
                topic="Portfolio Fit",
                must_include=["diversif", "correlation", "concentration", "risk", "return"],
                tags=["portfolio"],
            )
        )
    return out
