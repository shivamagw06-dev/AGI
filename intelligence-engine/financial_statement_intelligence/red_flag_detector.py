"""Red Flag Detector — Module 10.

Scans the rule library's "medium"/"high" severity findings for the
latest period, plus a handful of multi-period patterns that need the
full series (repeated equity dilution, sustained negative FCF, a large
one-off goodwill jump) that a single-period rule can't see. Every flag
carries Risk / Evidence / Confidence / Severity, per the brief.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from financial_statement_intelligence.deltas import compute_deltas
from financial_statement_intelligence.rule_library import evaluate_rules
from financial_statement_intelligence.schema import FinancialSeries

RED_FLAG_CATEGORIES = (
    "earnings_quality", "leverage", "liquidity", "working_capital",
    "acquisition_risk", "capital_structure", "cash_generation", "reinvestment_risk",
    "dividend_sustainability",
)


@dataclass
class RedFlag:
    risk: str
    evidence: str
    confidence: float
    severity: str
    category: str


def _single_period_flags(series: FinancialSeries) -> list[RedFlag]:
    prior, current = series.pair(lag=1)
    if prior is None or current is None:
        return []
    deltas = compute_deltas(prior, current)
    findings = evaluate_rules(deltas)
    flags: list[RedFlag] = []
    for f in findings:
        if f.severity not in ("medium", "high"):
            continue
        flags.append(
            RedFlag(
                risk=f.rule_id.replace("_", " "),
                evidence=f.explanation,
                confidence=f.confidence,
                severity=f.severity,
                category=f.category,
            )
        )
    return flags


def _repeated_equity_dilution(series: FinancialSeries) -> list[RedFlag]:
    periods = series.periods
    if len(periods) < 3:
        return []
    dilution_periods = 0
    for i in range(1, len(periods)):
        if periods[i].share_capital > periods[i - 1].share_capital * 1.02:
            dilution_periods += 1
    if dilution_periods >= 2:
        return [
            RedFlag(
                risk="repeated equity dilution",
                evidence=f"Share Capital increased in {dilution_periods} of the last {len(periods) - 1} periods — "
                f"repeated dilution of existing shareholders.",
                confidence=0.75,
                severity="medium",
                category="capital_structure",
            )
        ]
    return []


def _sustained_negative_fcf(series: FinancialSeries) -> list[RedFlag]:
    window = series.window(3)
    if len(window) < 2:
        return []
    negative_periods = sum(1 for p in window if p.free_cash_flow < 0)
    if negative_periods >= 2:
        return [
            RedFlag(
                risk="sustained negative free cash flow",
                evidence=f"Free Cash Flow was negative in {negative_periods} of the last {len(window)} periods — "
                f"a structural, not one-off, cash-consumption pattern.",
                confidence=0.8,
                severity="high",
                category="cash_generation",
            )
        ]
    return []


def _large_goodwill_jump(series: FinancialSeries) -> list[RedFlag]:
    prior, current = series.pair(lag=1)
    if prior is None or current is None or not current.total_assets:
        return []
    jump = current.goodwill - prior.goodwill
    if jump > 0.10 * current.total_assets:
        return [
            RedFlag(
                risk="large one-off goodwill increase",
                evidence=f"Goodwill increased by {jump:,.0f}, more than 10% of Total Assets ({current.total_assets:,.0f}), "
                f"in a single period — likely a material acquisition concentrating future impairment risk.",
                confidence=0.7,
                severity="medium",
                category="acquisition_risk",
            )
        ]
    return []


def _revenue_growth_without_cash(series: FinancialSeries) -> list[RedFlag]:
    prior, current = series.pair(lag=1)
    if prior is None or current is None:
        return []
    d = compute_deltas(prior, current)
    rev_pct, ocf_pct = d.pct("revenue"), d.pct("operating_cf")
    if rev_pct is not None and rev_pct > 0.10 and ocf_pct is not None and ocf_pct < 0:
        return [
            RedFlag(
                risk="revenue growth without cash",
                evidence=f"Revenue grew {rev_pct * 100:+.1f}% while Operating Cash Flow declined {ocf_pct * 100:.1f}% — "
                f"growth is not being converted into cash.",
                confidence=0.8,
                severity="high",
                category="earnings_quality",
            )
        ]
    return []


def detect_red_flags(series: FinancialSeries) -> dict[str, Any]:
    flags: list[RedFlag] = []
    flags.extend(_single_period_flags(series))
    flags.extend(_repeated_equity_dilution(series))
    flags.extend(_sustained_negative_fcf(series))
    flags.extend(_large_goodwill_jump(series))
    flags.extend(_revenue_growth_without_cash(series))

    # De-duplicate by risk label (multiple sources can catch the same thing).
    seen: set[str] = set()
    unique: list[RedFlag] = []
    for f in flags:
        if f.risk in seen:
            continue
        seen.add(f.risk)
        unique.append(f)

    high = [f for f in unique if f.severity == "high"]
    medium = [f for f in unique if f.severity == "medium"]

    return {
        "company": series.company,
        "total_flags": len(unique),
        "high_severity_count": len(high),
        "medium_severity_count": len(medium),
        "flags": [
            {"risk": f.risk, "evidence": f.evidence, "confidence": f.confidence, "severity": f.severity, "category": f.category}
            for f in sorted(unique, key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x.severity, 3))
        ],
    }
