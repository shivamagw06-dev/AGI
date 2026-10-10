"""Institutional Decision Engine V2 — schema constants (final architectural component)."""

from __future__ import annotations

IDEV2_VERSION = "2.0.0"
PROGRAMME = "AGIB_INSTITUTIONAL_DECISION_ENGINE_V2"
PROGRAMME_SHORT = "IDE_V2"
ARCHITECTURE_STATUS = "v1.0.1 LOCKED"
ARCHITECTURE_FROZEN = True
PRIMARY_QUESTION = "What is the highest-quality institutional decision?"
PRIMARY_QUESTION_ALT = "What is the best institutional decision given everything AGIB knows today?"

PIPELINE = [
    "Official Filings",
    "FIL",
    "FDI",
    "MII",
    "ACI",
    "EIL",
    "PIL",
    "CIG",
    "IKG",
    "FIE",
    "ILM",
    "SSL",
    "Institutional Analysts",
    "Investment Committee",
    "Portfolio Intelligence Office",
    "INSTITUTIONAL DECISION ENGINE V2",
    "CIO",
    "Research Writer",
    "ACS",
    "IRS",
    "Production",
]

# Soft inputs — referenced, never redesigned
INPUT_LAYERS = (
    "filing_intelligence",
    "filing_diff",
    "management_intelligence",
    "accounting_intelligence",
    "evidence_intelligence",
    "peer_intelligence",
    "causal_intelligence",
    "knowledge_graph",
    "forecast_intelligence",
    "institutional_memory",
    "simulation_lab",
    "institutional_analysts",
    "investment_committee",
    "portfolio_intelligence",
)

WEIGHT_DIMENSIONS = (
    "business",
    "financial",
    "valuation",
    "accounting",
    "management",
    "risk",
    "macro",
    "portfolio",
    "evidence",
    "forecast",
    "learning",
)

RECOMMENDATION_STATUSES = (
    "recommendation_ready",
    "further_research_required",
    "portfolio_unsuitable",
    "evidence_insufficient",
    "committee_review_required",
    "monitoring_required",
)

UNCERTAINTY_CLASSES = (
    "known",
    "known_unknown",
    "weak_evidence",
    "conflicting_evidence",
    "unknown_unknown",
)

CONSTITUTIONAL_CHAIN = (
    "evidence",
    "reasoning",
    "committee",
    "portfolio",
    "policy",
    "decision",
)

NO_REDESIGN = (
    "engine",
    "ui",
    "provider",
    "filing_intelligence",
    "filing_diff",
    "management_intelligence",
    "accounting_intelligence",
    "evidence_intelligence",
    "peer_intelligence",
    "causal_intelligence",
    "knowledge_graph",
    "forecast_intelligence",
    "institutional_memory",
    "simulation_lab",
    "portfolio_intelligence",
    "decision_engine",  # V1 left intact
    "institutional_analysts",
    "investment_committee",
    "cio",
    "research_writer",
    "certification",
    "regression",
    "institutional_stack",
)

# Architecture Freeze Review — answered before declaring AGIB v3 complete
FREEZE_REVIEW = {
    "filing_intelligence": {
        "responsibility": "What do the company's own filings actually say?",
        "duplicate": False,
        "output_owner": "FIL desk / stack",
        "audit_traceable": True,
        "evidence_backed": True,
    },
    "filing_diff": {
        "responsibility": "What materially changed since the previous filing?",
        "duplicate": False,
        "output_owner": "FDI desk / stack",
        "audit_traceable": True,
        "evidence_backed": True,
    },
    "management_intelligence": {
        "responsibility": "Can this management team be trusted to compound shareholder value?",
        "duplicate": False,
        "output_owner": "MII",
        "audit_traceable": True,
        "evidence_backed": True,
    },
    "accounting_intelligence": {
        "responsibility": "Can the financial statements be trusted?",
        "duplicate": False,
        "output_owner": "ACI",
        "audit_traceable": True,
        "evidence_backed": True,
    },
    "evidence_intelligence": {
        "responsibility": "What evidence supports each claim, and at what confidence?",
        "duplicate": False,
        "output_owner": "EIL",
        "audit_traceable": True,
        "evidence_backed": True,
    },
    "peer_intelligence": {
        "responsibility": "How does this company compare to the best and most relevant peers?",
        "duplicate": False,
        "output_owner": "PIL",
        "audit_traceable": True,
        "evidence_backed": True,
    },
    "causal_intelligence": {
        "responsibility": "Why did this happen?",
        "duplicate": False,
        "output_owner": "CIG",
        "audit_traceable": True,
        "evidence_backed": True,
    },
    "knowledge_graph": {
        "responsibility": "What is connected?",
        "duplicate": False,
        "output_owner": "IKG",
        "audit_traceable": True,
        "evidence_backed": True,
    },
    "forecast_intelligence": {
        "responsibility": "What future paths are plausible?",
        "duplicate": False,
        "output_owner": "FIE",
        "audit_traceable": True,
        "evidence_backed": True,
        "forecast_calibrated_over_time": True,
    },
    "institutional_memory": {
        "responsibility": "What has AGIB learned over time?",
        "duplicate": False,
        "output_owner": "ILM",
        "audit_traceable": True,
        "evidence_backed": True,
    },
    "simulation_lab": {
        "responsibility": "What happens if this decision is taken?",
        "duplicate": False,
        "output_owner": "SSL",
        "audit_traceable": True,
        "evidence_backed": True,
    },
    "institutional_analysts": {
        "responsibility": "Specialist desk opinions under mandates",
        "duplicate": False,
        "output_owner": "IAF",
        "audit_traceable": True,
        "evidence_backed": True,
    },
    "investment_committee": {
        "responsibility": "Structured debate, votes, minority views",
        "duplicate": False,
        "output_owner": "IC / ICI",
        "audit_traceable": True,
        "evidence_backed": True,
    },
    "portfolio_intelligence": {
        "responsibility": "Does this company improve this specific portfolio?",
        "duplicate": False,
        "output_owner": "PIO",
        "audit_traceable": True,
        "evidence_backed": True,
    },
    "decision_engine_v2": {
        "responsibility": "Constitutional orchestration of all layers into institutional judgement",
        "duplicate": False,
        "output_owner": "IDE V2",
        "audit_traceable": True,
        "evidence_backed": True,
        "reproducible_from_stored_inputs": True,
    },
    "cio": {
        "responsibility": "Communicate the institutional decision package",
        "duplicate": False,
        "output_owner": "CIO",
        "audit_traceable": True,
        "evidence_backed": True,
    },
    "post_freeze_rule": "Future work improves evidence, coverage, reasoning, analyst depth, calibration, learning — NOT new top-level intelligence layers",
}
