"""AGI Core v1.0 — machine-readable frozen baseline.

Human-readable twin: docs/AGI_CORE_V1_0.md

Status: Frozen
Regression: Production Release Gate
Owner: Core Platform

Future PRs must keep these contracts green via
`python -m ask_product_test.run_production_regression_v1`.
Deliberate behavior changes require a Core version bump.
"""

from __future__ import annotations

from typing import Any, Dict, List

AGI_CORE_VERSION = "1.0"
AGI_CORE_STATUS = "frozen"
AGI_CORE_OWNER = "Core Platform"
AGI_CORE_REGRESSION = "production_release_gate"
AGI_CORE_BASELINE_DATE = "2026-08-02"

FROZEN_COMPONENTS: List[Dict[str, str]] = [
    {
        "id": "financial_foundations",
        "name": "Financial Foundations",
        "module": "financial_foundations",
        "gate": "afi_acceptance",
    },
    {
        "id": "financial_intelligence",
        "name": "Financial Intelligence",
        "module": "financial_statement_intelligence",
        "gate": "afi_acceptance",
    },
    {
        "id": "financial_concepts",
        "name": "Financial Concepts",
        "module": "financial_concepts",
        "gate": "concept_acceptance",
    },
    {
        "id": "business_intelligence",
        "name": "Business Intelligence",
        "module": "business_intelligence.foundation",
        "gate": "bi_acceptance",
    },
    {
        "id": "knowledge_unification",
        "name": "Knowledge Unification",
        "module": "knowledge_unification",
        "gate": "kul_acceptance",
    },
    {
        "id": "coverage_intelligence",
        "name": "Coverage Intelligence",
        "module": "coverage_policy + capiq_ikt",
        "gate": "coverage_acceptance",
    },
]

# Permanent merge order for the Production Release Gate.
# Core v1.0 suites first; later main-line certs (industry / identity / platform)
# appended so the gate never drops coverage that production already requires.
RELEASE_GATE_ORDER: List[str] = [
    "founder_evaluation_v2",
    "golden_founder_5",
    "golden_business_20",
    "afi_acceptance",
    "bi_acceptance",
    "bi_integration",
    "ii_acceptance",
    "ii_integration",
    "founder_evaluation_v3",
    "coverage_acceptance",
    "concept_acceptance",
    "kul_acceptance",
    "recommendation_policy",
    "unknown_entity",
    "canonical_classification",
    "company_metadata_routing",
    "core_platform_acceptance",
    "answer_quality",
]

RELEASE_GATE_TARGETS: Dict[str, Dict[str, Any]] = {
    "founder_evaluation_v2": {"metric": "pass_rate_pct", "op": "gte", "value": 95.0},
    "golden_founder_5": {"metric": "pass_rate", "op": "eq", "value": 1.0},
    "golden_business_20": {"metric": "pass_rate_pct", "op": "eq", "value": 100.0},
    "afi_acceptance": {"metric": "overall_score_pct", "op": "gte", "value": 95.0},
    "bi_acceptance": {"metric": "pass_rate_pct", "op": "eq", "value": 100.0},
    "bi_integration": {"metric": "pass_rate_pct", "op": "eq", "value": 100.0},
    "ii_acceptance": {"metric": "pass_rate_pct", "op": "eq", "value": 100.0},
    "ii_integration": {"metric": "pass_rate_pct", "op": "eq", "value": 100.0},
    "founder_evaluation_v3": {"metric": "pass_rate_pct", "op": "gte", "value": 95.0},
    "coverage_acceptance": {"metric": "release_decision", "op": "eq", "value": "PASS"},
    "concept_acceptance": {"metric": "pass_rate_pct", "op": "eq", "value": 100.0},
    "kul_acceptance": {"metric": "pass_rate_pct", "op": "eq", "value": 100.0},
    "recommendation_policy": {"metric": "pass_rate_pct", "op": "eq", "value": 100.0},
    "unknown_entity": {"metric": "pass_rate_pct", "op": "eq", "value": 100.0},
    "canonical_classification": {"metric": "pass_rate_pct", "op": "eq", "value": 100.0},
    "company_metadata_routing": {"metric": "pass_rate_pct", "op": "eq", "value": 100.0},
    "core_platform_acceptance": {"metric": "overall_score", "op": "gte", "value": 98.0},
    "answer_quality": {"metric": "overall_score", "op": "gte", "value": 95.0},
}

BASELINE_RESULTS_INPROCESS: Dict[str, Any] = {
    "recorded_at": AGI_CORE_BASELINE_DATE,
    "mode": "inprocess",
    "release_decision": "PASS",
    "phase3_freeze_ready": True,
    "results": {
        "bi_acceptance": 100.0,
        "bi_integration": 100.0,
        "golden_business_20": 100.0,
        "golden_founder_5": 1.0,
        "founder_evaluation_v2": 100.0,
        "kul_acceptance": 100.0,
        "concept_acceptance": 100.0,
        "recommendation_policy": 100.0,
        "unknown_entity": 100.0,
        "coverage_acceptance": "PR_SCOPED_PASS",
        "afi_acceptance": 96.42,
        "hallucinations": 0,
    },
}

FREEZE_POLICY: Dict[str, Any] = {
    "status": AGI_CORE_STATUS,
    "version": AGI_CORE_VERSION,
    "owner": AGI_CORE_OWNER,
    "regression": AGI_CORE_REGRESSION,
    "allowed_without_version_bump": [
        "bug_fixes_restoring_baseline",
        "performance_without_answer_change",
        "coverage_expansion_without_weaker_refusal",
        "documentation_and_observability",
        "new_capabilities_outside_core_that_do_not_regress_gate",
    ],
    "requires_version_bump": [
        "changing_release_suite_expected_behavior_or_targets",
        "weakening_recommendation_unknown_or_coverage_policy",
        "bypassing_kul_for_core_financial_or_business_short_circuits",
        "dropping_or_relaxing_production_release_gate_suites",
    ],
    "merge_rule": "Production Release Gate PASS required before merge",
}


def baseline_manifest() -> Dict[str, Any]:
    return {
        "agi_core_version": AGI_CORE_VERSION,
        "status": AGI_CORE_STATUS,
        "owner": AGI_CORE_OWNER,
        "regression": AGI_CORE_REGRESSION,
        "baseline_date": AGI_CORE_BASELINE_DATE,
        "frozen_components": FROZEN_COMPONENTS,
        "release_gate_order": RELEASE_GATE_ORDER,
        "release_gate_targets": RELEASE_GATE_TARGETS,
        "baseline_results_inprocess": BASELINE_RESULTS_INPROCESS,
        "freeze_policy": FREEZE_POLICY,
        "docs": "docs/AGI_CORE_V1_0.md",
        "runner": "ask_product_test.run_production_regression_v1",
    }
