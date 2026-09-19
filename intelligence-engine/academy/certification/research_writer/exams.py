"""Research Writer (IRW) certification — Level 13 fidelity."""

from __future__ import annotations

from academy.certification.benchmark_suite.companies import BENCHMARK_COMPANIES
from academy.certification.schema import ExamSpec


def exams() -> list[ExamSpec]:
    out: list[ExamSpec] = []
    for i, co in enumerate(BENCHMARK_COMPANIES[:10]):
        out.append(
            ExamSpec(
                exam_id=f"acs_irw_{i+1:03d}",
                level=13,
                analyst="research_writer",
                question=(
                    f"Transform the Investment Committee package on {co['name']} into an institutional report "
                    f"without changing facts, confidence, odds or evidence."
                ),
                company=co["name"],
                ticker=co["ticker"],
                topic="IRW Fidelity",
                must_include=["committee", "report", "without changing", "evidence", "confidence"],
                tags=["research_writer", "irw"],
            )
        )
    return out
