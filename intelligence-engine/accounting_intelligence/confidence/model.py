"""Accounting Confidence model.

Confidence =
  Cash Quality (30%)
  + Earnings Quality (25%)
  + Working Capital (15%)
  + Accounting Consistency (15%)
  + Forensic Models (15%)
"""

from __future__ import annotations

from typing import Any

WEIGHTS = {
    "cash_quality": 0.30,
    "earnings_quality": 0.25,
    "working_capital": 0.15,
    "accounting_consistency": 0.15,
    "forensic": 0.15,
}


def accounting_confidence(
    *,
    cash_quality: float,
    earnings_quality: float,
    working_capital: float,
    accounting_consistency: float,
    forensic: float,
    evidence_coverage: float = 70.0,
    unknowns: list[str] | None = None,
) -> dict[str, Any]:
    comps = {
        "cash_quality": max(0.0, min(100.0, cash_quality)),
        "earnings_quality": max(0.0, min(100.0, earnings_quality)),
        "working_capital": max(0.0, min(100.0, working_capital)),
        "accounting_consistency": max(0.0, min(100.0, accounting_consistency)),
        "forensic": max(0.0, min(100.0, forensic)),
    }
    contributions = {k: round(comps[k] * WEIGHTS[k], 2) for k in comps}
    total = round(sum(contributions.values()), 2)
    return {
        "confidence": total,
        "breakdown": comps,
        "weights": WEIGHTS,
        "contributions": contributions,
        "evidence_coverage": evidence_coverage,
        "explain": (
            f"Cash {comps['cash_quality']:.0f}×30% + Earnings {comps['earnings_quality']:.0f}×25% + "
            f"WC {comps['working_capital']:.0f}×15% + Consistency {comps['accounting_consistency']:.0f}×15% + "
            f"Forensic {comps['forensic']:.0f}×15% = {total:.0f}"
        ),
        "unknowns": unknowns
        or [
            "Full multi-year cash-flow statement series still expanding via FIL",
            "Detailed DSO/DIO/DPO panels pending denser filing tables",
        ],
    }
