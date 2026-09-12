"""AGIB Phase 2 — Institutional Investment Intelligence Programme registry.

Baseline v1.0 is FROZEN. This package declares Phase 2 workstreams only.
It must not modify Constitution, Governance Spec, Decision Engine, Gate,
Evaluation Lab, Drift, or IAT methodology.
"""

from __future__ import annotations

PROGRAMME = "AGIB_PHASE2_INSTITUTIONAL_INVESTMENT_INTELLIGENCE"
PROGRAMME_VERSION = "phase2-investment-intelligence-programme-v1.0.0"
ARCHITECTURE_TARGET = "extends_baseline_v1_0"
BASELINE_NAME = "AGIB Institutional Baseline v1.0"
BASELINE_STATUS = "FROZEN"

PRIMARY_OBJECTIVE = (
    "Increase the quality, depth, accuracy, and explainability of "
    "institutional investment research without modifying Phase 1 governance."
)

# Paths / components that Phase 2 PRs must not redesign.
FROZEN_BASELINE_LOCKS = {
    "constitution": "frozen",
    "governance_spec": "frozen",
    "decision_engine_contracts": "frozen",
    "institutional_gate": "frozen",
    "recommendation_readiness_methodology": "frozen",
    "institutional_readiness_methodology": "frozen",
    "analytical_confidence_methodology": "frozen",
    "evaluation_lab": "frozen",
    "drift_engine": "frozen",
    "institutional_acceptance_test": "frozen",
    "mission_control_release_dashboard": "frozen",
}

SUCCESS_CRITERIA = (
    "recommendation_quality_improves",
    "analytical_confidence_improves",
    "institutional_readiness_improves_where_evidence_increases",
    "evidence_coverage_improves",
    "forecast_quality_improves",
    "valuation_quality_improves",
    "ownership_quality_improves",
    "no_governance_regression",
    "unknown_drift_zero",
    "iat_continues_to_pass",
)

DOC_PATH = "docs/PHASE2_INSTITUTIONAL_INVESTMENT_INTELLIGENCE_PROGRAMME.md"
