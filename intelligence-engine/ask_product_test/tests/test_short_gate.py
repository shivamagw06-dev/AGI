"""The short gate must measure the product, or refuse to run."""

from __future__ import annotations

import asyncio

import pytest

from ask_product_test import provider_stub
from ask_product_test import routing_failure_taxonomy as tax
from ask_product_test import run_short_gate as sg
from ask_product_test import zero_defect_extract as zde
from ask_product_test.core_platform_acceptance_v1 import build_cases


def test_it_runs_the_whole_universe_not_the_failing_cases():
    """4 hallucinations and 2 namesakes are today's count, not the test set."""
    cases = zde.select_cases(build_cases(), defects=zde.REQUIRED_DEFECTS)
    bank = build_cases()
    assert len(cases) == len([c for c in bank
                              if c["section"] == "J_impossible" or c.get("ticker")])
    assert all(c["section"] == "J_impossible" or c.get("ticker") for c in cases)
    assert len([c for c in cases if c["section"] == "J_impossible"]) == \
        len([c for c in bank if c["section"] == "J_impossible"]), "every J_impossible case"


def test_the_namesake_universe_is_complete_and_a_wrong_binding_is_p0():
    from ask_product_test.company_metadata_routing_acceptance_v1 import FALLTHROUGH_CASES

    rows = [{
        "kind": "fallthrough",
        "question": question,
        "passed": question != FALLTHROUGH_CASES[0],
        "failed": (["bound_namesake:WRONG"]
                   if question == FALLTHROUGH_CASES[0] else []),
    } for question in FALLTHROUGH_CASES]
    normalised = sg.normalise_namesake_results(rows)
    assert len(normalised) == len(FALLTHROUGH_CASES) == 6
    assert sum(bool(r["flags"].get("wrong_entity")) for r in normalised) == 1

    report = sg.build_report(normalised, elapsed=1.0,
                             cases_planned=len(normalised), stub_ok=True)
    assert report["defects"]["wrong_entity"] == 1
    assert report["unique_p0_cases"] == 1
    assert report["decision"] == "FAIL"


def test_a_missing_namesake_case_is_infrastructure_not_partial_coverage():
    from ask_product_test.company_metadata_routing_acceptance_v1 import FALLTHROUGH_CASES

    rows = [{"kind": "fallthrough", "question": q, "failed": []}
            for q in FALLTHROUGH_CASES[:-1]]
    with pytest.raises(RuntimeError, match="namesake universe mismatch"):
        sg.normalise_namesake_results(rows)


def test_a_missing_stub_is_infrastructure_not_not_run(monkeypatch):
    """NOT_RUN belongs to optional live evaluation, never to a required lane."""
    monkeypatch.setenv("ASK_TEST_MODE", "inprocess")
    monkeypatch.setattr("ask_product_test.provider_stub.install", lambda: False)
    assert sg.main() == sg.EXIT_INFRASTRUCTURE


def test_contract_mode_is_infrastructure_not_a_green_result(monkeypatch):
    """In contract mode the harness never reaches the engine.

    Every case fails for one reason and the counters read zero defects - a
    green result produced by not running the product.
    """
    monkeypatch.setenv("ASK_TEST_MODE", "contract")
    assert sg.main() == sg.EXIT_INFRASTRUCTURE


def test_installed_stub_uses_pipeline_context_not_expected_case_data():
    """A bad pipeline binding must not be corrected by the test's ground truth."""
    provider = provider_stub.StubEditorialProvider()
    result = asyncio.run(provider.rewrite(
        question="Explain the expected company",
        structured={
            "company": "Wrongly Bound Industries",
            "ticker": "WRONG",
            "financial_quality": "Weak",
        },
    ))
    assert "Wrongly Bound Industries" in result["text"]
    assert "ticker: WRONG" in result["text"]
    assert "expected company is covered" not in result["text"].lower()


def test_unique_cases_and_label_counts_are_reported_separately():
    """A case can carry several labels; neither number may stand for the other."""
    results = [
        {"id": "a", "failed": ["no_honest_uncertainty", "thin_answer"]},
        {"id": "b", "failed": ["not_routed_to_metadata"]},
        {"id": "c", "failed": []},
    ]
    report = sg.build_report(results, elapsed=1.0, cases_planned=3, stub_ok=True)
    assert report["unique_failing_cases"] == 2
    assert report["label_occurrences"] == 3
    assert report["unique_p0_cases"] == 1, "only the hallucinating case is P0"


def test_routing_and_missing_metadata_are_kept_and_not_p0():
    results = [{"id": "r", "failed": ["not_routed_to_metadata"]},
               {"id": "m", "failed": ["expected_value_missing"]}]
    report = sg.build_report(results, elapsed=1.0, cases_planned=2, stub_ok=True)
    assert report["non_p0_categories"] == {tax.ROUTING: 1, tax.MISSING_METADATA: 1}
    assert report["zero_defect"] is True, "neither makes a release unsafe"
    assert report["decision"] == "PASS"
    assert report["unique_failing_cases"] == 2, "still reported, not discarded"


def test_a_hallucination_fails_the_report():
    report = sg.build_report([{"id": "h", "failed": ["no_honest_uncertainty"]}],
                             elapsed=1.0, cases_planned=1, stub_ok=True)
    assert report["zero_defect"] is False
    assert report["decision"] == "FAIL"
    assert report["defects"]["hallucination"] == 1


def test_the_report_blocks_nothing():
    report = sg.build_report([], elapsed=1.0, cases_planned=0, stub_ok=True)
    assert report["report_only"] is True
    assert report["blocks_merge"] is False
    assert report["blocks_deployment"] is False
    assert report["required_check"] is False


def test_the_budget_is_reported_not_enforced():
    report = sg.build_report([], elapsed=sg.BUDGET_SECONDS + 100,
                             cases_planned=0, stub_ok=True)
    assert report["within_budget"] is False
    assert report["decision"] == "PASS", "over budget must not fail a report-only gate"


def test_the_mapping_is_still_provisional():
    report = sg.build_report([], elapsed=1.0, cases_planned=0, stub_ok=True)
    assert "PROVISIONAL" in report["section_mapping"]


# --- fixed budget ----------------------------------------------------------

def test_the_environment_cannot_raise_the_budget(monkeypatch, capsys):
    monkeypatch.setenv("SHORT_GATE_BUDGET_SEC", str(sg.BUDGET_SECONDS + 5000))
    assert sg.budget_seconds() == sg.BUDGET_SECONDS
    assert "ignoring" in capsys.readouterr().out


def test_the_environment_may_lower_the_budget(monkeypatch):
    monkeypatch.setenv("SHORT_GATE_BUDGET_SEC", "60")
    assert sg.budget_seconds() == 60


def test_a_malformed_override_falls_back_to_the_committed_ceiling(monkeypatch):
    monkeypatch.setenv("SHORT_GATE_BUDGET_SEC", "later")
    assert sg.budget_seconds() == sg.BUDGET_SECONDS


# --- partitioning ----------------------------------------------------------

def test_partitions_recombine_to_exactly_the_manifest():
    cases = zde.select_cases(build_cases(), defects=zde.REQUIRED_DEFECTS)
    for shards in (1, 2, 3, 4, 8):
        buckets = sg.partition(cases, shards)
        check = sg.verify_partition(cases, buckets)
        assert check["matches_manifest"] is True, f"{shards} shards"
        assert check["combined_cases"] == len(cases)
        assert check["duplicates"] == 0 and not check["missing"] and not check["extra"]


def test_a_dropped_shard_is_detected():
    """The failure this check exists for: a lost shard reads as zero defects."""
    cases = zde.select_cases(build_cases(), defects=zde.REQUIRED_DEFECTS)
    buckets = sg.partition(cases, 4)
    check = sg.verify_partition(cases, buckets[:-1])
    assert check["matches_manifest"] is False
    assert check["missing"], "the lost cases must be named"


def test_a_duplicated_case_is_detected():
    cases = zde.select_cases(build_cases(), defects=zde.REQUIRED_DEFECTS)
    buckets = sg.partition(cases, 3)
    buckets.append([buckets[0][0]])
    check = sg.verify_partition(cases, buckets)
    assert check["matches_manifest"] is False and check["duplicates"] == 1


def test_partitioning_never_reduces_coverage():
    cases = zde.select_cases(build_cases(), defects=zde.REQUIRED_DEFECTS)
    total = sum(len(b) for b in sg.partition(cases, 6))
    assert total == len(cases) == 395


def test_four_shard_reports_recombine_to_all_401_checks():
    cases = zde.select_cases(build_cases(), defects=zde.REQUIRED_DEFECTS)
    buckets = sg.partition(cases, 4)
    full_manifest = sorted(sg.manifest(cases) + sg.namesake_manifest_ids())
    reports = []
    for index, bucket in enumerate(buckets):
        ids = sg.manifest(bucket)
        if index == 0:
            ids += sg.namesake_manifest_ids()
        results = [{"id": case_id, "failed": [], "flags": {}} for case_id in ids]
        reports.append(sg.build_report(
            results, elapsed=100 + index, cases_planned=len(full_manifest),
            stub_ok=True, manifest_ids=full_manifest,
            shard_index=index, shard_count=4))
    combined = sg.combine_reports(reports)
    assert combined["coverage_complete"] is True
    assert combined["cases_planned"] == combined["cases_evaluated"] == 401
    assert combined["decision"] == "PASS"
    assert combined["elapsed_seconds"] == 103.0


def test_combiner_rejects_a_missing_or_duplicated_case():
    manifest_ids = ["a", "b"]
    reports = [
        sg.build_report([{"id": "a", "failed": []}], elapsed=1,
                        cases_planned=2, stub_ok=True,
                        manifest_ids=manifest_ids, shard_index=0, shard_count=2),
        sg.build_report([{"id": "a", "failed": []}], elapsed=1,
                        cases_planned=2, stub_ok=True,
                        manifest_ids=manifest_ids, shard_index=1, shard_count=2),
    ]
    with pytest.raises(ValueError, match="coverage mismatch"):
        sg.combine_reports(reports)


def test_invalid_shard_coordinates_are_infrastructure(monkeypatch):
    monkeypatch.setenv("SHORT_GATE_SHARD_COUNT", "4")
    monkeypatch.setenv("SHORT_GATE_SHARD_INDEX", "4")
    with pytest.raises(ValueError, match="invalid shard"):
        sg.shard_config()
