"""Financial Statement Intelligence Engine — the Module 1/2/3/4/7/9/10
integration point.

Given a ``FinancialSeries``, this is the single call that answers:
"is this company improving or deteriorating, and why?" It combines the
rule library's findings for the latest period, ratio trends across the
whole series, and multi-window trend comparison (QoQ/YoY/3yr/5yr —
Module 9), then classifies overall direction with evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from financial_statement_intelligence.deltas import compute_deltas
from financial_statement_intelligence.ratio_engine import growth_metrics, ratio_trends
from financial_statement_intelligence.rule_library import Finding, evaluate_rules
from financial_statement_intelligence.schema import FinancialSeries


@dataclass
class PeriodInterpretation:
    label: str
    prior_label: Optional[str]
    findings: list[Finding]
    positive_count: int
    concern_count: int


def interpret_period(series: FinancialSeries, *, index: int = -1) -> PeriodInterpretation:
    """Module 1-4/6/7/10: interpret one period against its predecessor."""
    idx = index if index >= 0 else len(series.periods) + index
    if idx <= 0 or idx >= len(series.periods):
        return PeriodInterpretation(
            label=series.periods[idx].label if series.periods else "n/a",
            prior_label=None, findings=[], positive_count=0, concern_count=0,
        )
    prior, current = series.periods[idx - 1], series.periods[idx]
    deltas = compute_deltas(prior, current)
    findings = evaluate_rules(deltas)
    positive = sum(1 for f in findings if f.severity == "positive")
    concern = sum(1 for f in findings if f.severity in ("medium", "high"))
    return PeriodInterpretation(
        label=current.label, prior_label=prior.label, findings=findings,
        positive_count=positive, concern_count=concern,
    )


def interpret_series(series: FinancialSeries) -> dict[str, Any]:
    """Interpret every consecutive period pair in the series."""
    interpretations = [interpret_period(series, index=i) for i in range(1, len(series.periods))]
    return {
        "company": series.company,
        "sector": series.sector,
        "periods_analyzed": [p.label for p in series.periods],
        "period_interpretations": [
            {
                "label": pi.label,
                "prior_label": pi.prior_label,
                "positive_count": pi.positive_count,
                "concern_count": pi.concern_count,
                "findings": [
                    {
                        "rule_id": f.rule_id, "category": f.category, "module": f.module,
                        "severity": f.severity, "confidence": f.confidence,
                        "explanation": f.explanation, "evidence": f.evidence,
                    }
                    for f in pi.findings
                ],
            }
            for pi in interpretations
        ],
    }


# ---------------------------------------------------------------------------
# Module 9 — Trend Analysis (QoQ / YoY / 3yr / 5yr)
# ---------------------------------------------------------------------------
def _window_summary(prior, current) -> dict[str, Any]:
    d = compute_deltas(prior, current)
    return {
        "available": True,
        "from": prior.label,
        "to": current.label,
        "revenue_change": d.pct("revenue"),
        "ebitda_change": d.pct("ebitda"),
        "pat_change": d.pct("pat"),
        "gross_margin_change": d.get("ratio_gross_margin").abs_change if d.get("ratio_gross_margin") else None,
        "ebitda_margin_change": d.get("ratio_ebitda_margin").abs_change if d.get("ratio_ebitda_margin") else None,
        "net_debt_to_ebitda_change": d.get("ratio_net_debt_to_ebitda").abs_change if d.get("ratio_net_debt_to_ebitda") else None,
        "roic_change": d.get("ratio_roic").abs_change if d.get("ratio_roic") else None,
    }


def trend_windows(series: FinancialSeries) -> dict[str, Any]:
    """Compare the latest period against 1, 3, and 5 periods back, plus the
    full-series ratio trend classification and growth CAGRs (Module 9:
    QoQ/YoY/3yr/5yr). When a series is shorter than 4/6 periods, a
    "vs_full_window" comparison (earliest vs latest) still lets the
    acceleration/deceleration questions be answered from whatever history
    is actually available, instead of silently going empty."""
    windows: dict[str, Any] = {}
    for lag, name in ((1, "vs_prior_period"), (3, "vs_3_periods_ago"), (5, "vs_5_periods_ago")):
        prior, current = series.pair(lag=lag)
        windows[name] = _window_summary(prior, current) if (prior is not None and current is not None) else {"available": False}

    if len(series.periods) >= 3:
        windows["vs_full_window"] = _window_summary(series.periods[0], series.periods[-1])
    else:
        windows["vs_full_window"] = {"available": False}

    trends = ratio_trends(series)
    windows["ratio_trend_summary"] = {t.key: t.direction for t in trends}
    windows["growth"] = growth_metrics(series)
    windows["questions"] = _trend_questions(windows)
    return windows


def _trend_questions(windows: dict[str, Any]) -> dict[str, str]:
    """Module 9's four framing questions, answered from the computed windows."""
    recent = windows.get("vs_prior_period") or {}
    older = windows.get("vs_5_periods_ago") if (windows.get("vs_5_periods_ago") or {}).get("available") else None
    older = older or (windows.get("vs_3_periods_ago") if (windows.get("vs_3_periods_ago") or {}).get("available") else None)
    older = older or (windows.get("vs_full_window") if (windows.get("vs_full_window") or {}).get("available") else None)
    older = older or {}

    def _accel(current_key: str) -> str:
        r, o = recent.get(current_key), older.get(current_key)
        if r is None or o is None:
            return "insufficient data across periods to compare"
        if r > o:
            return f"accelerating ({r * 100:+.1f}% most recent vs {o * 100:+.1f}% over the longer window)"
        if r < o:
            return f"decelerating ({r * 100:+.1f}% most recent vs {o * 100:+.1f}% over the longer window)"
        return "steady"

    trend_summary = windows.get("ratio_trend_summary") or {}
    return {
        "is_growth_accelerating": f"Revenue growth is {_accel('revenue_change')}.",
        "are_margins_expanding": f"EBITDA margin trend is {trend_summary.get('ebitda_margin', 'insufficient_data')} "
        f"across the series; Gross margin trend is {trend_summary.get('gross_margin', 'insufficient_data')}.",
        "is_leverage_improving": f"Net Debt/EBITDA trend is {trend_summary.get('net_debt_to_ebitda', 'insufficient_data')}; "
        f"Interest Coverage trend is {trend_summary.get('interest_coverage', 'insufficient_data')}.",
        "is_capital_efficiency_increasing": f"ROIC trend is {trend_summary.get('roic', 'insufficient_data')}; "
        f"ROCE trend is {trend_summary.get('roce', 'insufficient_data')}.",
    }


def overall_direction(series: FinancialSeries) -> dict[str, Any]:
    """Success criterion 1: is this company improving or deteriorating?"""
    interp = interpret_period(series, index=-1)
    trends = ratio_trends(series)
    improving = sum(1 for t in trends if t.direction == "improving")
    deteriorating = sum(1 for t in trends if t.direction == "deteriorating")
    net_score = (interp.positive_count - interp.concern_count) + (improving - deteriorating)
    if net_score >= 3:
        verdict = "improving"
    elif net_score <= -3:
        verdict = "deteriorating"
    else:
        verdict = "mixed"
    return {
        "verdict": verdict,
        "net_score": net_score,
        "latest_period_positive_findings": interp.positive_count,
        "latest_period_concern_findings": interp.concern_count,
        "ratios_improving": improving,
        "ratios_deteriorating": deteriorating,
        "evidence": [f.explanation for f in interp.findings][:8],
    }
