"""ICE-01 — Investment Committee Engine constants."""

from __future__ import annotations

ICE_WORKSTREAM_ID = "ICE-01"
ICE_PRODUCT = "Investment Committee Engine"
ICE_VERSION = "ice-01-v1.0.0"
ICE_SPEC = "docs/AGI_ICE_01_INVESTMENT_COMMITTEE.md"
ICE_ROLE = "deterministic_committee_governance"
COMMITTEE_ENGINE_VERSION = "ice-01-committee-engine-v1"
VALIDATOR_VERSION = "ice-01-validator-v1"
DEFAULT_PORTFOLIO_ID = "agi-core-equity"
DEFAULT_COMMITTEE_ID = "agi-investment-committee"

RESOLUTION_STATUSES = (
    "Pending Review",
    "Approved",
    "Approved with Conditions",
    "Rejected",
    "Deferred",
    "Escalated",
)

VOTE_CHOICES = (
    "APPROVE",
    "APPROVE_WITH_CONDITIONS",
    "REJECT",
    "DEFER",
    "ESCALATE",
    "REQUIRES_REVIEW",
)

VOTING_DESKS = ("Risk", "Policy", "Allocation")

LINEAGE_CHAIN = (
    "Committee",
    "Resolution",
    "Portfolio Decision",
    "Policy Assessment",
    "Portfolio Risk",
    "Evidence",
)
