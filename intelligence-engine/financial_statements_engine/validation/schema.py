"""FSE-05 VFQE contracts."""

from __future__ import annotations

WORKSTREAM_ID = "FSE-05"
VERSION = "1.0.0"
SUBSYSTEM = "validation_financial_quality_engine"
PROGRAMME = "Financial Statements Engine"
VALIDATOR_VERSION = "vfqe-v1.0.0"

ISSUES_RECOMMENDATIONS = False
RECOMMENDATION_POLICY = "validation_gatekeeper_no_buy_sell_never_edits_drafts"

SEVERITIES = ("INFO", "WARNING", "ERROR", "CRITICAL")
APPROVAL_STATES = ("APPROVED", "APPROVED_WITH_WARNINGS", "REJECTED", "QUARANTINED")
GRADES = ("A+", "A", "B", "C", "D", "Fail")

# ERROR blocks publication by default for VFQE (CRITICAL always blocks)
BLOCK_ON_ERROR = True

# Soft relative tolerance for accounting identities
ACCOUNTING_TOLERANCE = 0.05

# Statistical thresholds (warnings only)
STAT_THRESHOLDS = {
    "revenue_growth_abs_pct": 200.0,  # vs prior when available
    "forbid_negative_depreciation": True,
    "forbid_negative_inventory": True,
    "forbid_negative_share_capital": True,
}

SCORE_WEIGHTS = {
    "structural_quality": 0.20,
    "accounting_integrity": 0.25,
    "coverage_quality": 0.15,
    "temporal_consistency": 0.10,
    "statistical_health": 0.10,
    "parser_confidence": 0.20,
}

QUALITY_TARGETS = {
    "validation_determinism": 1.0,
    "rule_reproducibility": 1.0,
    "validation_traceability": 1.0,
    "approval_auditability": 1.0,
    "quality_score_explainability": 1.0,
}
