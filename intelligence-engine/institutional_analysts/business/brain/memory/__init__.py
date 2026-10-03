"""Business Analyst memory package — trajectory + long-term opinion timeline."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from institutional_analysts.business.brain.memory.opinion_timeline import (
    get_timeline,
    quality_series,
    record_opinion,
    reset_for_tests as reset_timeline_for_tests,
)
from institutional_analysts.business.brain.memory.trajectory import (
    build_memory_record as _build,
    compare_views as _compare,
    extract_prior_view,
)


def compare_views(
    *,
    current_stance: str,
    current_quality_grade: str,
    current_moat_durability: str,
    current_confidence: float,
    prior: Dict[str, Any],
    current_growth_view: str = "",
    current_risks: Optional[List[str]] = None,
) -> Dict[str, Any]:
    return _compare(
        current_stance=current_stance,
        current_quality_grade=current_quality_grade,
        current_moat_durability=current_moat_durability,
        current_growth_view=current_growth_view,
        current_risks=list(current_risks or []),
        current_confidence=current_confidence,
        prior=prior,
    )


def build_memory_record(
    *,
    company: str,
    stance: str,
    quality_grade: str,
    moat_durability: str,
    confidence: float,
    opinion_summary: str,
    comparison: Dict[str, Any],
    prior: Dict[str, Any],
    growth_view: str = "",
    risks: Optional[List[str]] = None,
) -> Dict[str, Any]:
    return _build(
        company=company,
        stance=stance,
        quality_grade=quality_grade,
        moat_durability=moat_durability,
        growth_view=growth_view,
        risks=list(risks or []),
        confidence=confidence,
        opinion_summary=opinion_summary,
        comparison=comparison,
        prior=prior,
    )


def reset_for_tests() -> None:
    reset_timeline_for_tests()


__all__ = [
    "extract_prior_view",
    "compare_views",
    "build_memory_record",
    "record_opinion",
    "get_timeline",
    "quality_series",
    "reset_for_tests",
]
