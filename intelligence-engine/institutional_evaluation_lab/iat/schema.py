"""Phase 1 Institutional Acceptance Test (IAT) — final exam for baseline readiness.

Consume-only. Does not alter Decision Engine, Constitution, Governance Spec,
scoring, weights, reasoning, or valuation/technical models.
"""

from __future__ import annotations

IAT_VERSION = "institutional-acceptance-test-v1.0.0"
PROGRAMME = "AGIB_PHASE1_INSTITUTIONAL_ACCEPTANCE_TEST"
ARCHITECTURE_VERSION = "v1.0"
BASELINE_NAME = "AGIB Institutional Baseline v1.0"

# Golden universe composition required for the official exam.
REQUIRED_UNIVERSE_N = 200
REQUIRED_BUCKETS = {
    "nifty_50": 50,
    "nifty_next_50": 50,
    "midcap": 50,
    "smallcap": 25,
    "special_situation": 25,
}

SCOPE_LOCKS = {
    "decision_engine": "read_only",
    "constitution": "read_only",
    "governance_spec": "read_only",
    "scoring": "read_only",
    "weights": "read_only",
    "reasoning": "read_only",
    "valuation_models": "read_only",
    "technical_models": "read_only",
    "acceptance_exam_only": True,
}

# Baseline qualification thresholds (official exam).
THRESHOLDS = {
    "universe_n": REQUIRED_UNIVERSE_N,
    "governance_critical_fail_max": 0,
    "editorial_violations_max": 0,
    "gate_enforcement_pct_min": 100.0,
    "constitution_enforced": True,
    "spec_compliance_pct_min": 100.0,
    "evidence_coverage_pct_min": 70.0,
    "evidence_freshness_pct_min": 70.0,
    "lineage_pct_min": 90.0,
    "source_attribution_pct_min": 80.0,
    "unknown_drift_max": 0,
    "drift_budget_must_pass": True,
    "replay_inputs_pct_min": 80.0,
    "structured_failure_pct_min": 90.0,  # among failed rows
    "avg_runtime_s_max": 15.0,
}

BASELINE_INCLUDES = (
    "Constitution",
    "Governance Spec",
    "Decision Engine",
    "Institutional Gate",
    "Evaluation Lab",
    "Drift Engine",
    "Release Observability",
    "Mission Control",
)
