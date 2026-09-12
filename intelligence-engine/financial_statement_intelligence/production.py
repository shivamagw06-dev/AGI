"""Financial Statement Intelligence — production facade.

Soft-wire only. Not a recommendation engine; not wired into Ask's
answer composition. Standalone analyst-reasoning engine that consumes a
``FinancialSeries`` (built directly, via ``adapters`` from Phase 1, or
from any structured fundamentals feed).
"""

from __future__ import annotations

from typing import Any, Optional

from financial_statement_intelligence.case_studies import analyse_case_study, list_case_studies
from financial_statement_intelligence.earnings_quality import assess_earnings_quality
from financial_statement_intelligence.health_score import score_financial_health
from financial_statement_intelligence.industry_lens import industry_context, list_sectors
from financial_statement_intelligence.metric_concepts import all_metrics, get_metric
from financial_statement_intelligence.narrative_generator import generate_narrative
from financial_statement_intelligence.ratio_engine import compute_ratios, growth_metrics, ratio_trends
from financial_statement_intelligence.red_flag_detector import detect_red_flags
from financial_statement_intelligence.rule_library import rule_library
from financial_statement_intelligence.schema import FSI_VERSION, FREEZE_LOCKS, PROGRAMME, RELEASE_STATUS, FinancialSeries
from financial_statement_intelligence.statement_intelligence import (
    interpret_series,
    overall_direction,
    trend_windows,
)


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "fsi_version": FSI_VERSION,
        "freeze_locks": FREEZE_LOCKS,
        "release_status": RELEASE_STATUS,
        "api_prefix": "/v1/financial-statement-intelligence",
        "modules": [
            "1 Income Statement Intelligence", "2 Balance Sheet Intelligence", "3 Cash Flow Intelligence",
            "4 Statement Linkage Analysis", "5 Ratio Intelligence", "6 Earnings Quality",
            "7 Working Capital Intelligence", "8 Margin Analysis", "9 Trend Analysis",
            "10 Red Flag Detection", "11 Industry Interpretation", "12 Analyst Narrative Generation",
            "13 Case Studies", "14 Financial Health Score", "15 Examination",
        ],
        "fabricated": False,
    }


def dashboard() -> dict[str, Any]:
    return {
        "fsi_version": FSI_VERSION,
        "rule_library_size": len(rule_library()),
        "metric_concepts": len(all_metrics()),
        "case_studies": len(list_case_studies()),
        "sectors_covered": list_sectors(),
        "fabricated": False,
    }


def explain_metric(key: str) -> dict[str, Any]:
    card = get_metric(key.strip().lower().replace(" ", "_"))
    if not card:
        return {"found": False, "key": key}
    return {
        "found": True, "key": card.key, "module": card.module, "title": card.title,
        "definition": card.definition, "formula": card.formula, "drivers": card.drivers,
        "interpretation": card.interpretation, "industry_differences": card.industry_differences,
        "common_distortions": card.common_distortions,
    }


def analyze(series: FinancialSeries) -> dict[str, Any]:
    """The single call that ties every engine together for one company."""
    return {
        "company": series.company,
        "sector": series.sector,
        "data_source": series.data_source,
        "overall_direction": overall_direction(series),
        "statement_interpretation": interpret_series(series),
        "trend_analysis": trend_windows(series),
        "ratios_latest": compute_ratios(series),
        "growth": growth_metrics(series),
        "earnings_quality": assess_earnings_quality(series),
        "red_flags": detect_red_flags(series),
        "financial_health_score": score_financial_health(series),
        "narrative": generate_narrative(series),
        "industry_context": industry_context(series.sector) if series.sector else {"found": False},
    }


def ratios(series: FinancialSeries) -> dict[str, Any]:
    return {"latest": compute_ratios(series), "trends": [
        {"key": t.key, "title": t.title, "values": t.values, "labels": t.labels,
         "direction": t.direction, "interpretation": t.interpretation, "warning": t.warning}
        for t in ratio_trends(series)
    ]}


def earnings_quality(series: FinancialSeries) -> dict[str, Any]:
    return assess_earnings_quality(series)


def red_flags(series: FinancialSeries) -> dict[str, Any]:
    return detect_red_flags(series)


def health_score(series: FinancialSeries) -> dict[str, Any]:
    return score_financial_health(series)


def narrative(series: FinancialSeries, *, drivers: Optional[dict[str, float]] = None) -> dict[str, Any]:
    return generate_narrative(series, drivers=drivers)


def sector_context(sector: str) -> dict[str, Any]:
    return industry_context(sector)


def case_studies() -> dict[str, Any]:
    return {"n": len(list_case_studies()), "case_studies": list_case_studies(), "fabricated": False}


def case_study(key: str) -> dict[str, Any]:
    return analyse_case_study(key)


def soft_slice_for_ask_agi(question: str, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
    """Non-invasive Ask soft-wire: surface a metric explanation when the
    question matches Phase 2 vocabulary. Never overrides Ask's executive."""
    low = question.strip().lower().replace(" ", "_")
    hit = explain_metric(low)
    if hit.get("found"):
        return {"enabled": True, "financial_statement_intelligence": hit}
    for key in all_metrics():
        if key.replace("_", " ") in question.lower():
            return {"enabled": True, "financial_statement_intelligence": explain_metric(key)}
    return {"enabled": False}
