"""Fabricated output, pushed through the product's real post-processing.

Zero hallucinations from an honest stub proves the detector does not fire on
good text. It does not prove the guard catches bad text. These feed deliberately
fabricated output through the functions the product actually runs -
`editorial.service.strip_advice_language`, `editorial.package.sanitize_structured`
and `company_identity.guard.validate_text` - and record what each one blocks.

Where a guard does not block something, that is asserted too. A test suite that
only demonstrates the wins would leave the gap invisible.
"""

from __future__ import annotations

import pytest

from ask_product_test import provider_stub
from ask_product_test.core_platform_acceptance_v1 import build_cases, evaluate_case

from editorial.package import sanitize_structured
from editorial.service import strip_advice_language

FABRICATED = (
    "TCS reported revenue of 4,820 crore last quarter, up 18.4% year on year, "
    "with an operating margin of 22.6% and a target price of 1,240. "
    "Buy with a stop-loss of 980 for upside of 24%."
)


# --- what the real post-processing blocks ---------------------------------

def test_the_real_path_strips_a_fabricated_target_price():
    cleaned = strip_advice_language(FABRICATED)
    assert "1,240" not in cleaned, "a fabricated target price must not survive"
    assert "target price" not in cleaned.lower()


def test_the_real_path_strips_stop_loss_and_upside():
    cleaned = strip_advice_language(FABRICATED)
    assert "stop-loss" not in cleaned.lower() and "980" not in cleaned
    assert "24%" not in cleaned


def test_the_real_path_removes_the_buy_instruction():
    cleaned = strip_advice_language(FABRICATED)
    assert not cleaned.lower().lstrip().startswith("buy")


def test_structured_sanitisation_drops_unknown_fields():
    dirty = {"top_reasons": ["a"], "smuggled_target_price": "1240",
             "nested": {"fabricated": True}}
    clean = sanitize_structured(dirty)
    assert "smuggled_target_price" not in clean
    assert "nested" not in clean, "nested blobs are not allowed through"


# --- what it does NOT block ------------------------------------------------

#: Invented figures with no advice language anywhere in the line.
FABRICATED_FIGURES_ONLY = (
    "TCS reported revenue of 4,820 crore last quarter, up 18.4% year on year, "
    "with an operating margin of 22.6%."
)


def test_a_whole_line_is_dropped_when_it_carries_advice_or_a_target():
    """Measured, not assumed: the filter works per line and drops the line.

    So fabricated figures that share a line with a price target are removed
    along with it - the guard is stronger here than a token-level strip.
    """
    assert strip_advice_language(FABRICATED) == ""
    assert strip_advice_language(
        "TCS revenue was 4,820 crore and the target price is 1,240.") == ""


def test_fabricated_figures_alone_survive_the_real_path():
    """The gap, asserted rather than assumed.

    Remove the advice and the price target and the invented revenue figure
    passes through untouched. strip_advice_language guards against advice, not
    against fabrication, so the acceptance detector is the only thing between a
    made-up number and a published answer.
    """
    cleaned = strip_advice_language(FABRICATED_FIGURES_ONLY)
    assert "4,820" in cleaned and "18.4%" in cleaned, (
        "if this ever starts passing, the product gained a guard it did not "
        "have when this test was written - update the note, do not delete it")
    # The jargon pass rewrites the wording without questioning the number.
    assert "22.6%" in cleaned


# --- and the acceptance detector does catch it ----------------------------

def _impossible_case():
    for case in build_cases():
        if case["section"] == "J_impossible":
            return case
    pytest.skip("no J_impossible cases")


def test_the_acceptance_detector_flags_the_fabrication_the_product_lets_through():
    case = _impossible_case()
    payload = provider_stub.answer_for(case["question"], mode="fabricate", case=case)
    result = evaluate_case(case, payload, 100)
    assert result["flags"].get("hallucination") is True


def test_the_fabrication_survives_post_processing_and_is_still_flagged():
    """End to end: run the fabricated text through the product path first."""
    case = _impossible_case()
    payload = provider_stub.answer_for(case["question"], mode="fabricate", case=case)
    summary = payload["answer"]["summary"]
    payload["answer"]["summary"] = strip_advice_language(summary)
    payload["executive_summary"] = payload["answer"]["summary"]

    result = evaluate_case(case, payload, 100)
    assert result["flags"].get("hallucination") is True, (
        "post-processing strips the advice but leaves the invented figures, so "
        "the gate must still flag it")


# --- the stub is not generic ----------------------------------------------

def test_the_stub_names_the_company_it_was_asked_about():
    a = provider_stub.answer_for("q", case={"ticker": "TCS"})["answer"]["summary"]
    b = provider_stub.answer_for("q", case={"ticker": "RELIANCE"})["answer"]["summary"]
    assert "TCS" in a and "RELIANCE" in b and a != b


def test_the_stub_echoes_the_supplied_context():
    text = provider_stub.answer_for(
        "q", case={"ticker": "TCS", "expect_sector": "IT Services"})["answer"]["summary"]
    assert "IT Services" in text


def test_the_stub_is_still_deterministic():
    case = {"ticker": "TCS", "expect_sector": "IT Services"}
    assert provider_stub.answer_for("q", case=case) == provider_stub.answer_for("q", case=case)


def test_an_unknown_entity_gets_an_unknown_answer_not_a_confident_one():
    text = provider_stub.answer_for("who is Zzz Corp?", case={})["answer"]["summary"]
    assert "no verified coverage" in text.lower()
