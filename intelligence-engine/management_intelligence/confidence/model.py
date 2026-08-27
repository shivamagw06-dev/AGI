"""Management Confidence model.

Confidence =
  Credibility (35%)
  + Execution (25%)
  + Capital Allocation (20%)
  + Governance (10%)
  + Communication (10%)
"""

from __future__ import annotations

from typing import Any

WEIGHTS = {
    "credibility": 0.35,
    "execution": 0.25,
    "capital_allocation": 0.20,
    "governance": 0.10,
    "communication": 0.10,
}


def management_confidence(
    *,
    credibility: float,
    execution: float,
    capital_allocation: float,
    governance: float,
    communication: float,
    evidence_coverage: float = 70.0,
) -> dict[str, Any]:
    comps = {
        "credibility": max(0.0, min(100.0, credibility)),
        "execution": max(0.0, min(100.0, execution)),
        "capital_allocation": max(0.0, min(100.0, capital_allocation)),
        "governance": max(0.0, min(100.0, governance)),
        "communication": max(0.0, min(100.0, communication)),
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
            f"Credibility {comps['credibility']:.0f}×35% + Execution {comps['execution']:.0f}×25% + "
            f"Capital {comps['capital_allocation']:.0f}×20% + Governance {comps['governance']:.0f}×10% + "
            f"Communication {comps['communication']:.0f}×10% = {total:.0f}"
        ),
        "unknowns": [
            "Full multi-year transcript claim ledger still expanding",
            "Detailed compensation tables pending denser FIL ingest",
        ],
    }
