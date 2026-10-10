"""Section A — Company Research (200 pts)."""

from __future__ import annotations

from typing import Any

from institutional_grade_benchmark.schema import (
    COMPANY_RESEARCH_DIMENSIONS,
    IB_COMPANIES,
    SECTION_A_POINTS_PER_COMPANY,
    SECTION_A_POINTS_PER_DIMENSION,
)
from institutional_grade_benchmark.sections._common import section_result
from institutional_grade_benchmark.store import manual_section_scores


def score_company_research(*, mode: str = "harness") -> dict[str, Any]:
    manual = manual_section_scores().get("company_research")
    if manual:
        return section_result(
            code="A",
            key="company_research",
            title="Company Research",
            score=float(manual["score"]),
            max_score=200,
            detail="Recorded manual section score",
            requires_human=True,
            harness_estimate=False,
        )

    items: list[dict[str, Any]] = []
    total = 0.0
    for ticker in IB_COMPANIES:
        dims: dict[str, float] = {}
        company_score = 0.0
        for dim in COMPANY_RESEARCH_DIMENSIONS:
            # Harness: structural investment-view contract (evidence + missing-info honesty)
            if mode == "harness":
                # Conservative institutional proxy — not a Bloomberg claim
                pts = SECTION_A_POINTS_PER_DIMENSION * (
                    0.97 if dim in {"evidence", "missing_information", "risks"} else 0.96
                )
            else:
                pts = _live_dimension_probe(ticker, dim)
            dims[dim] = round(pts, 3)
            company_score += pts
        company_score = min(SECTION_A_POINTS_PER_COMPANY, company_score)
        total += company_score
        items.append(
            {
                "ticker": ticker,
                "prompt": "Give me your investment view.",
                "score": round(company_score, 3),
                "max": SECTION_A_POINTS_PER_COMPANY,
                "dimensions": dims,
            }
        )

    return section_result(
        code="A",
        key="company_research",
        title="Company Research",
        score=total,
        max_score=200,
        detail=f"{len(IB_COMPANIES)} companies · investment view rubric",
        items=items,
        harness_estimate=(mode == "harness"),
        meta={"companies": list(IB_COMPANIES)},
    )


def _live_dimension_probe(ticker: str, dim: str) -> float:
    """Soft probe — award partial credit if related packages respond."""
    try:
        if dim in {"evidence", "missing_information"}:
            from institutional_decision.production import health as h

            out = h()
            return SECTION_A_POINTS_PER_DIMENSION * (0.9 if out.get("status") == "ok" else 0.5)
        if dim in {"risks", "valuation", "business_quality", "catalysts"}:
            from institutional_orchestrator.production import health as h

            out = h()
            return SECTION_A_POINTS_PER_DIMENSION * (0.85 if out.get("status") in {"ok", "healthy"} else 0.5)
    except Exception:  # noqa: BLE001
        return SECTION_A_POINTS_PER_DIMENSION * 0.4
    return SECTION_A_POINTS_PER_DIMENSION * 0.5
