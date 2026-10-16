"""Earnings Quality Engine — Module 6 (dedicated).

Detects high vs low quality earnings via four independently-computed
signals: cash conversion, accruals ratio, revenue/receivable divergence,
and EBITDA/capex divergence. Produces a 0-10 score with evidence, not a
bare label.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from financial_statement_intelligence.deltas import compute_deltas
from financial_statement_intelligence.schema import FinancialSeries, StatementPeriod


@dataclass
class QualitySignal:
    key: str
    label: str
    value: Optional[float]
    passed: bool
    weight: float
    explanation: str


def _cash_conversion_signal(prior: StatementPeriod, current: StatementPeriod) -> QualitySignal:
    ratio = (current.operating_cf / current.pat) if current.pat and abs(current.pat) > 1e-9 else None
    passed = ratio is not None and ratio >= 0.8
    return QualitySignal(
        "cash_conversion", "Operating Cash Flow / PAT", ratio, passed, 0.35,
        f"Operating Cash Flow covers {ratio * 100:.0f}% of PAT" if ratio is not None
        else "PAT is zero/negative — cash conversion ratio undefined",
    )


def _accruals_signal(prior: StatementPeriod, current: StatementPeriod) -> QualitySignal:
    """Accruals Ratio = (PAT − Operating CF) / Total Assets — lower is higher quality."""
    if not current.total_assets:
        return QualitySignal("accruals_ratio", "Accruals Ratio", None, True, 0.25, "Total Assets unavailable")
    accruals = (current.pat - current.operating_cf) / current.total_assets
    passed = accruals <= 0.05
    return QualitySignal(
        "accruals_ratio", "Accruals Ratio", round(accruals, 4), passed, 0.25,
        f"Accruals Ratio of {accruals * 100:.1f}% of Total Assets "
        + ("is within the healthy range (≤5%)" if passed else "exceeds 5% — a meaningful share of profit is not backed by cash"),
    )


def _revenue_receivable_signal(prior: StatementPeriod, current: StatementPeriod) -> QualitySignal:
    d = compute_deltas(prior, current)
    rev_pct, ar_pct = d.pct("revenue"), d.pct("receivables")
    if rev_pct is None or ar_pct is None:
        return QualitySignal("revenue_receivable_divergence", "Revenue vs Receivables Growth", None, True, 0.2, "insufficient data")
    gap = ar_pct - rev_pct
    passed = gap <= 0.10
    return QualitySignal(
        "revenue_receivable_divergence", "Revenue vs Receivables Growth", round(gap, 4), passed, 0.2,
        f"Receivables grew {gap * 100:+.1f} percentage points {'faster than' if gap > 0 else 'slower than'} Revenue"
        + (" — possible aggressive revenue recognition" if not passed else ""),
    )


def _ebitda_capex_signal(prior: StatementPeriod, current: StatementPeriod) -> QualitySignal:
    d = compute_deltas(prior, current)
    ebitda_pct, capex_pct = d.pct("ebitda"), d.pct("capex")
    if ebitda_pct is None or capex_pct is None:
        return QualitySignal("ebitda_capex_divergence", "EBITDA vs Capex Growth", None, True, 0.2, "insufficient data")
    gap = capex_pct - ebitda_pct
    passed = gap <= 0.25
    return QualitySignal(
        "ebitda_capex_divergence", "EBITDA vs Capex Growth", round(gap, 4), passed, 0.2,
        f"Capex grew {gap * 100:+.1f} percentage points {'faster than' if gap > 0 else 'slower than'} EBITDA"
        + (" — future depreciation risk building" if not passed else ""),
    )


def assess_earnings_quality(series: FinancialSeries) -> dict[str, Any]:
    """Module 6: 0-10 earnings quality score with the four signals as evidence."""
    prior, current = series.pair(lag=1)
    if prior is None or current is None:
        return {"available": False, "reason": "Need at least two periods to assess earnings quality."}

    signals = [
        _cash_conversion_signal(prior, current),
        _accruals_signal(prior, current),
        _revenue_receivable_signal(prior, current),
        _ebitda_capex_signal(prior, current),
    ]
    score = 10.0 * sum(s.weight for s in signals if s.passed)
    score = round(min(10.0, max(0.0, score)), 1)

    if score >= 8:
        label = "High quality"
    elif score >= 5:
        label = "Moderate quality — some caution flags"
    else:
        label = "Low quality — cash conversion and/or accrual signals are weak"

    return {
        "available": True,
        "period": current.label,
        "score": score,
        "label": label,
        "signals": [
            {
                "key": s.key, "label": s.label, "value": s.value,
                "passed": s.passed, "weight": s.weight, "explanation": s.explanation,
            }
            for s in signals
        ],
        "confidence": 0.7 if all(s.value is not None for s in signals) else 0.4,
    }
