"""AGI Core v1.0 baseline contract tests."""

from __future__ import annotations

from ask_product_test.agi_core_v1_0 import (
    AGI_CORE_STATUS,
    AGI_CORE_VERSION,
    FROZEN_COMPONENTS,
    RELEASE_GATE_ORDER,
    RELEASE_GATE_TARGETS,
    baseline_manifest,
)


def test_agi_core_is_frozen_v1():
    assert AGI_CORE_VERSION == "1.0"
    assert AGI_CORE_STATUS == "frozen"


def test_frozen_components_cover_core_stack():
    ids = {c["id"] for c in FROZEN_COMPONENTS}
    assert ids == {
        "financial_foundations",
        "financial_intelligence",
        "financial_concepts",
        "business_intelligence",
        "knowledge_unification",
        "coverage_intelligence",
    }


def test_release_gate_order_matches_permanent_policy():
    assert RELEASE_GATE_ORDER[0] == "founder_evaluation_v2"
    assert RELEASE_GATE_ORDER[1] == "golden_founder_5"
    assert RELEASE_GATE_ORDER[2] == "golden_business_20"
    assert RELEASE_GATE_ORDER[3] == "afi_acceptance"
    # Core identity/platform certs absorbed from main run after unknown-entity.
    assert "unknown_entity" in RELEASE_GATE_ORDER
    assert RELEASE_GATE_ORDER[-1] == "answer_quality"
    assert RELEASE_GATE_ORDER[-2] == "core_platform_acceptance"
    assert set(RELEASE_GATE_ORDER) == set(RELEASE_GATE_TARGETS)
    for required in (
        "ii_acceptance",
        "ii_integration",
        "founder_evaluation_v3",
        "canonical_classification",
        "company_metadata_routing",
    ):
        assert required in RELEASE_GATE_ORDER


def test_baseline_manifest_is_merge_ready():
    m = baseline_manifest()
    assert m["status"] == "frozen"
    assert m["owner"] == "Core Platform"
    assert m["regression"] == "production_release_gate"
    assert m["baseline_results_inprocess"]["release_decision"] == "PASS"
    assert m["freeze_policy"]["merge_rule"]
