"""Financial Health Scoring Engine — Module 14.

Eight 0-10 sub-scores (Financial Quality, Cash Generation, Profitability,
Leverage, Working Capital, Capital Efficiency, Earnings Quality, Growth)
combining into one 0-100 Overall Financial Strength score. Every
sub-score carries evidence, an explanation, a confidence, and its
historical trend direction — never a bare number.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from financial_statement_intelligence.earnings_quality import assess_earnings_quality
from financial_statement_intelligence.ratio_engine import compute_ratios, growth_metrics, ratio_trends
from financial_statement_intelligence.red_flag_detector import detect_red_flags
from financial_statement_intelligence.schema import FinancialSeries

Band = tuple[float, float]  # (threshold, score_at_or_beyond_threshold)


def _band_score(value: Optional[float], bands: list[Band], *, higher_is_better: bool) -> float:
    """bands sorted ascending by threshold; each entry's score applies once
    value crosses that threshold (in the direction of higher_is_better)."""
    if value is None:
        return 5.0  # neutral default when data is unavailable
    ordered = sorted(bands, key=lambda b: b[0], reverse=not higher_is_better)
    score = ordered[0][1] if higher_is_better else ordered[-1][1]
    for threshold, band_score in sorted(bands, key=lambda b: b[0]):
        if higher_is_better and value >= threshold:
            score = band_score
        elif not higher_is_better and value <= threshold:
            score = band_score
    return round(score, 1)


@dataclass
class SubScore:
    key: str
    title: str
    score: float
    evidence: list[str]
    explanation: str
    confidence: float
    historical_trend: str


def _trend_for(trends: dict[str, str], *keys: str) -> str:
    directions = [trends.get(k) for k in keys if trends.get(k) and trends.get(k) != "insufficient_data"]
    if not directions:
        return "insufficient_data"
    if all(d == "improving" for d in directions):
        return "improving"
    if all(d == "deteriorating" for d in directions):
        return "deteriorating"
    return "mixed"


def _financial_quality(ratios: dict, trends: dict[str, str]) -> SubScore:
    current_ratio_score = _band_score(ratios.get("current_ratio"), [(0.8, 2), (1.0, 5), (1.5, 8), (2.0, 10)], higher_is_better=True)
    interest_cov_score = _band_score(ratios.get("interest_coverage"), [(1.0, 2), (2.0, 5), (4.0, 8), (8.0, 10)], higher_is_better=True)
    score = round((current_ratio_score + interest_cov_score) / 2, 1)
    return SubScore(
        "financial_quality", "Financial Quality", score,
        [f"Current Ratio {ratios.get('current_ratio')}", f"Interest Coverage {ratios.get('interest_coverage')}"],
        "Blends near-term liquidity (Current Ratio) with debt-servicing headroom (Interest Coverage).",
        0.75 if ratios.get("current_ratio") is not None else 0.4,
        _trend_for(trends, "current_ratio", "interest_coverage"),
    )


def _cash_generation(series: FinancialSeries, ratios: dict, trends: dict[str, str]) -> SubScore:
    latest = series.latest()
    ocf, fcf = (latest.operating_cf if latest else None), (latest.free_cash_flow if latest else None)
    ocf_score = 10.0 if (ocf or 0) > 0 else 2.0
    fcf_score = 10.0 if (fcf or 0) > 0 else 2.0
    score = round((ocf_score + fcf_score) / 2, 1)
    return SubScore(
        "cash_generation", "Cash Generation", score,
        [f"Operating Cash Flow {ocf}", f"Free Cash Flow {fcf}"],
        "Rewards positive Operating Cash Flow and Free Cash Flow — the cash actually available to the business.",
        0.8, _trend_for(trends, "free_cash_flow"),
    )


def _profitability(ratios: dict, trends: dict[str, str]) -> SubScore:
    roe_score = _band_score(ratios.get("roe"), [(0.0, 2), (0.08, 5), (0.15, 8), (0.22, 10)], higher_is_better=True)
    net_margin_score = _band_score(ratios.get("net_margin"), [(0.0, 2), (0.05, 5), (0.12, 8), (0.20, 10)], higher_is_better=True)
    score = round((roe_score + net_margin_score) / 2, 1)
    return SubScore(
        "profitability", "Profitability", score,
        [f"ROE {ratios.get('roe')}", f"Net Margin {ratios.get('net_margin')}"],
        "Blends returns to shareholders (ROE) with bottom-line conversion (Net Margin).",
        0.75, _trend_for(trends, "roe", "net_margin"),
    )


def _leverage(ratios: dict, trends: dict[str, str]) -> SubScore:
    de_score = _band_score(ratios.get("debt_to_equity"), [(0.3, 10), (0.8, 8), (1.5, 5), (2.5, 2)], higher_is_better=False)
    ndebitda_score = _band_score(ratios.get("net_debt_to_ebitda"), [(1.0, 10), (2.0, 8), (3.5, 5), (5.0, 2)], higher_is_better=False)
    score = round((de_score + ndebitda_score) / 2, 1)
    return SubScore(
        "leverage", "Leverage", score,
        [f"Debt/Equity {ratios.get('debt_to_equity')}", f"Net Debt/EBITDA {ratios.get('net_debt_to_ebitda')}"],
        "Lower leverage scores higher — measures reliance on debt relative to equity and earnings capacity.",
        0.75, _trend_for(trends, "debt_to_equity", "net_debt_to_ebitda"),
    )


def _working_capital(ratios: dict, trends: dict[str, str]) -> SubScore:
    ccc_score = _band_score(ratios.get("cash_conversion_cycle"), [(0, 10), (30, 8), (60, 5), (100, 2)], higher_is_better=False)
    current_score = _band_score(ratios.get("current_ratio"), [(0.8, 2), (1.0, 5), (1.5, 8), (2.0, 10)], higher_is_better=True)
    score = round((ccc_score + current_score) / 2, 1)
    return SubScore(
        "working_capital", "Working Capital", score,
        [f"Cash Conversion Cycle {ratios.get('cash_conversion_cycle')} days", f"Current Ratio {ratios.get('current_ratio')}"],
        "Rewards a short cash conversion cycle and adequate current-asset coverage.",
        0.7, _trend_for(trends, "cash_conversion_cycle", "current_ratio"),
    )


def _capital_efficiency(ratios: dict, trends: dict[str, str]) -> SubScore:
    roic_score = _band_score(ratios.get("roic"), [(0.0, 2), (0.08, 5), (0.15, 8), (0.20, 10)], higher_is_better=True)
    roce_score = _band_score(ratios.get("roce"), [(0.0, 2), (0.10, 5), (0.18, 8), (0.25, 10)], higher_is_better=True)
    score = round((roic_score + roce_score) / 2, 1)
    return SubScore(
        "capital_efficiency", "Capital Efficiency", score,
        [f"ROIC {ratios.get('roic')}", f"ROCE {ratios.get('roce')}"],
        "ROIC vs an implied cost-of-capital hurdle and ROCE together measure how efficiently capital is deployed.",
        0.7, _trend_for(trends, "roic", "roce"),
    )


def _earnings_quality_subscore(series: FinancialSeries) -> SubScore:
    eq = assess_earnings_quality(series)
    if not eq.get("available"):
        return SubScore("earnings_quality", "Earnings Quality", 5.0, [], eq.get("reason", ""), 0.3, "insufficient_data")
    return SubScore(
        "earnings_quality", "Earnings Quality", eq["score"],
        [s["explanation"] for s in eq["signals"]],
        eq["label"],
        eq["confidence"], "insufficient_data",
    )


def _growth(series: FinancialSeries) -> SubScore:
    g = growth_metrics(series)
    if not g.get("available"):
        return SubScore("growth", "Growth", 5.0, [], "Need at least two periods to assess growth.", 0.3, "insufficient_data")
    rev_score = _band_score(g.get("revenue_cagr"), [(-0.05, 2), (0.0, 4), (0.08, 7), (0.15, 10)], higher_is_better=True)
    fcf_score = _band_score(g.get("fcf_cagr"), [(-0.10, 2), (0.0, 5), (0.10, 8), (0.20, 10)], higher_is_better=True)
    score = round((rev_score + fcf_score) / 2, 1)
    trend = "improving" if score >= 7 else ("deteriorating" if score <= 3 else "mixed")
    return SubScore(
        "growth", "Growth", score,
        [f"Revenue CAGR {g.get('revenue_cagr')}", f"FCF CAGR {g.get('fcf_cagr')}", f"EPS CAGR {g.get('eps_cagr')}"],
        f"Revenue CAGR of {g.get('revenue_cagr')} and FCF CAGR of {g.get('fcf_cagr')} over {g.get('years')} period(s).",
        0.7, trend,
    )


def score_financial_health(series: FinancialSeries) -> dict[str, Any]:
    latest = series.latest()
    if latest is None:
        return {"available": False, "reason": "No periods in series."}
    ratios = compute_ratios(series)
    trend_directions = {t.key: t.direction for t in ratio_trends(series)}

    subscores = [
        _financial_quality(ratios, trend_directions),
        _cash_generation(series, ratios, trend_directions),
        _profitability(ratios, trend_directions),
        _leverage(ratios, trend_directions),
        _working_capital(ratios, trend_directions),
        _capital_efficiency(ratios, trend_directions),
        _earnings_quality_subscore(series),
        _growth(series),
    ]
    overall = round(sum(s.score for s in subscores) / len(subscores) * 10, 1)
    red_flags = detect_red_flags(series)

    return {
        "available": True,
        "company": series.company,
        "period": latest.label,
        "overall_financial_strength": overall,
        "max_overall": 100,
        "sub_scores": [
            {
                "key": s.key, "title": s.title, "score": s.score, "max_score": 10,
                "evidence": s.evidence, "explanation": s.explanation,
                "confidence": s.confidence, "historical_trend": s.historical_trend,
            }
            for s in subscores
        ],
        "red_flag_summary": {
            "total": red_flags["total_flags"],
            "high_severity": red_flags["high_severity_count"],
            "medium_severity": red_flags["medium_severity_count"],
        },
    }
