"""PCE-01 — Institutional Policy & Constraint Engine constants."""

from __future__ import annotations

PCE_WORKSTREAM_ID = "PCE-01"
PCE_PRODUCT = "Institutional Policy & Constraint Engine"
PCE_VERSION = "pce-01-v1.0.0"
PCE_SPEC = "docs/AGI_PCE_01_POLICY_CONSTRAINT.md"
PCE_ROLE = "deterministic_policy_governance"
POLICY_ENGINE_VERSION = "pce-01-policy-engine-v1"
VALIDATOR_VERSION = "pce-01-validator-v1"
DEFAULT_PORTFOLIO_ID = "agi-core-equity"
DEFAULT_POLICY_PROFILE = "family_office"

OVERALL_STATUS = ("Compliant", "Warning", "Breach", "Critical Breach")

POLICY_PROFILES = (
    "family_office",
    "balanced",
    "conservative",
    "growth",
    "pms",
    "mutual_fund",
    "custom",
)

LINEAGE_CHAIN = (
    "Portfolio",
    "Holding",
    "Portfolio Risk",
    "Policy Constraint",
    "Company Decision",
    "Reason",
    "Evidence",
)
