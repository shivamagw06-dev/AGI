"""The extracted zero-defect checks must still catch what the long suite caught."""

from __future__ import annotations

import pytest

from ask_product_test import provider_stub, zero_defect_extract as zde
from ask_product_test.core_platform_acceptance_v1 import build_cases, evaluate_case


# --- 1. the hallucination checks still detect ------------------------------

def _impossible_case():
    for case in build_cases():
        if case["section"] == "J_impossible":
            return case
    pytest.skip("no J_impossible cases in the bank")


def test_a_fabricating_answer_is_caught_as_a_hallucination():
    """The detector, exercised through the extract rather than described."""
    case = _impossible_case()
    payload = provider_stub.answer_for(case["question"], mode="fabricate")
    result = evaluate_case(case, payload, 100)
    assert result["flags"].get("hallucination") is True
    assert "no_honest_uncertainty" in result["failed"]


def test_an_honest_answer_is_not_a_hallucination():
    case = _impossible_case()
    payload = provider_stub.answer_for(case["question"], mode="honest")
    result = evaluate_case(case, payload, 100)
    assert not result["flags"].get("hallucination")


def test_the_extract_counts_the_same_defects_the_long_suite_counts():
    """Four hallucinating answers must be reported as four.

    The run that produced the register counted 4. This asserts the extracted
    path arrives at the same number from the same flags, so moving the check out
    of the 28-minute suite does not quietly lose it.
    """
    case = _impossible_case()
    bad = provider_stub.answer_for(case["question"], mode="fabricate")
    good = provider_stub.answer_for(case["question"], mode="honest")
    results = [evaluate_case(case, bad, 100) for _ in range(4)]
    results += [evaluate_case(case, good, 100) for _ in range(20)]

    report = zde.summarise(results, defects=["hallucination"], provider_ok=True)
    assert report["defects"]["hallucination"] == 4
    assert report["decision"] == "FAIL"
    assert len(report["offenders"]["hallucination"]) == 4


def test_zero_hallucinations_is_a_pass():
    case = _impossible_case()
    good = provider_stub.answer_for(case["question"], mode="honest")
    report = zde.summarise([evaluate_case(case, good, 100) for _ in range(10)],
                           defects=["hallucination"], provider_ok=True)
    assert report["defects"]["hallucination"] == 0
    assert report["decision"] == "PASS"


# --- section mapping -------------------------------------------------------

def test_hallucination_is_confined_to_the_impossible_section():
    assert zde.sections_for(["hallucination"]) == ["J_impossible"]


def test_wrong_entity_is_reported_as_not_section_confined():
    """The honest answer: it fires wherever a case resolves an identity.

    A section-filtered extract would under-report it, so the extract must say it
    cannot be confined rather than pretend a subset covers it.
    """
    assert zde.sections_for(["wrong_entity"]) is None
    assert zde.DEFECT_SECTIONS["wrong_entity"] is None


def test_selection_keeps_every_identity_case_when_a_defect_is_unconfinable():
    cases = build_cases()
    chosen = zde.select_cases(cases, defects=["hallucination", "wrong_entity"])
    with_ticker = [c for c in cases if c.get("ticker")]
    assert len(chosen) >= len(with_ticker)


def test_the_mapping_is_labelled_provisional():
    report = zde.summarise([], defects=["hallucination"], provider_ok=True)
    assert "PROVISIONAL" in report["section_mapping"]


# --- 3. missing provider is never a product score -------------------------

def test_a_missing_provider_is_not_run_rather_than_zero():
    """A configuration problem must not be reported as a quality result."""
    report = zde.summarise([], defects=["hallucination"], provider_ok=False)
    assert report["decision"] == "NOT_RUN"
    assert "template fallback" in report["reason"]


def test_a_missing_provider_is_not_run_even_when_cases_look_clean(monkeypatch):
    case = _impossible_case()
    good = provider_stub.answer_for(case["question"], mode="honest")
    results = [evaluate_case(case, good, 100) for _ in range(5)]
    report = zde.summarise(results, defects=["hallucination"], provider_ok=False)
    assert report["decision"] == "NOT_RUN", "clean fallback output is not a PASS"


def test_provider_detection_reads_the_environment(monkeypatch):
    for name in zde.MISSING_PROVIDER_ENV:
        monkeypatch.delenv(name, raising=False)
    assert zde.provider_configured() is False
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    assert zde.provider_configured() is True


# --- 4. the stub is deterministic -----------------------------------------

def test_the_stub_returns_the_same_answer_every_time():
    a = provider_stub.answer_for("what is the revenue of an unknown company?")
    b = provider_stub.answer_for("what is the revenue of an unknown company?")
    assert a == b


def test_the_stub_can_produce_a_defect_so_the_detector_can_be_proven():
    """A stub that only produces good answers cannot demonstrate a check works."""
    assert provider_stub.answer_for("q", mode="fabricate") != \
        provider_stub.answer_for("q", mode="honest")


# --- 5. report-only --------------------------------------------------------

def test_the_extract_blocks_nothing():
    report = zde.summarise([], defects=["hallucination"], provider_ok=True)
    assert report["report_only"] is True
    assert report["blocks_merge"] is False
    assert report["blocks_deployment"] is False
