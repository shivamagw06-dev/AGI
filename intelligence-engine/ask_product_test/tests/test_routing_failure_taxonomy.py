"""A score is not a diagnosis: 51.47% does not make 33 failures equally urgent."""

from __future__ import annotations

from ask_product_test.routing_failure_taxonomy import (HALLUCINATION, MISSING_METADATA,
                                                       REGISTRY_GAP, ROUTING,
                                                       WRONG_COMPANY, categorise, classify)


def test_binding_the_wrong_company_is_wrong_company():
    assert categorise("bound_namesake") == WRONG_COMPANY
    assert categorise("wrong_value:INFY!=TCS") == WRONG_COMPANY


def test_never_reaching_the_metadata_engine_is_routing_not_wrong_data():
    """25 of 33 failing cases are this. It is one defect, not 25 data errors."""
    assert categorise("not_routed_to_metadata") == ROUTING
    assert categorise("wrong_intent:research") == ROUTING
    assert categorise("wrong_sources:['x']") == ROUTING


def test_a_registry_gap_is_not_an_answer_defect():
    """The registry not carrying a field is coverage, not a wrong answer."""
    assert categorise("field_missing_in_registry") == REGISTRY_GAP


def test_a_missing_value_is_distinct_from_a_wrong_one():
    assert categorise("expected_value_missing") == MISSING_METADATA
    assert categorise("field_not_answered:sector") == MISSING_METADATA


def test_hallucination_labels_are_release_critical():
    assert categorise("no_honest_uncertainty") == HALLUCINATION
    assert categorise("fabricated_specifics") == HALLUCINATION


def test_the_real_distribution_is_mostly_routing():
    """The shape measured from the actual run artifact.

    33 failing cases carrying 45 labels: 37 routing, 6 missing metadata,
    2 wrong-company. Calling all 33 P0 would spend the effort on routing.
    """
    results = (
        [{"id": f"r{i}", "failed": ["not_routed_to_metadata"]} for i in range(25)]
        + [{"id": f"i{i}", "failed": ["wrong_intent:x"]} for i in range(6)]
        + [{"id": f"s{i}", "failed": ["wrong_sources:y"]} for i in range(6)]
        + [{"id": f"m{i}", "failed": ["expected_value_missing"]} for i in range(6)]
        + [{"id": f"n{i}", "failed": ["bound_namesake"]} for i in range(2)]
    )
    out = classify(results)
    assert out["by_category"][ROUTING] == 37
    assert out["by_category"][MISSING_METADATA] == 6
    assert out["by_category"][WRONG_COMPANY] == 2
    assert out["release_critical_labels"] == 2, "2, not 33"


def test_a_passing_case_is_not_counted():
    assert classify([{"id": "ok", "failed": []}])["failing_cases"] == 0


def test_an_unknown_label_is_reported_rather_than_absorbed():
    out = classify([{"id": "x", "failed": ["something_new"]}])
    assert out["by_category"].get("unclassified") == 1
