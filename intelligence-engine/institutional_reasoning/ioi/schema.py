"""IOI schema — Institutional Outcome Intelligence Phase 6 targets."""

from __future__ import annotations

from typing import Any

IOI_VERSION = "institutional-outcome-intelligence-v1.0.0"
MODULE_CODE = "IOI"
PROGRAMME = "Institutional Outcome Intelligence"

DECISION_STATUSES = (
    "open",
    "under_review",
    "evaluated",
    "closed",
    "withheld",
)

PHASE6_TARGETS: dict[str, float] = {
    "outcome_suite": 95.0,
    "traceability": 100.0,
    "unattributed_failures": 0.0,
}

# Seed IES confidence (implementation quality) — not updated by outcomes.
IES_CONFIDENCE: dict[str, float] = {
    "rel_val_damodaran": 0.98,
    "hist_multiples": 0.97,
    "margin_of_safety": 0.96,
    "dcf_applicability": 0.96,
    "business_quality_roic": 0.97,
    "accounting_quality_screen": 0.95,
    "peer_comparison": 0.94,
    "macro": 0.90,
    "scenario": 0.91,
    "policy": 0.93,
    "sizing": 0.92,
}


def ies_confidence(framework_id: str) -> float:
    return float(IES_CONFIDENCE.get(framework_id, 0.90))
