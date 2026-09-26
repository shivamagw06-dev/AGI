"""Concept lookup — aliases, natural-language phrasing, search ranking."""

from __future__ import annotations

import pytest

from financial_concepts.lookup import explain, search

ALIAS_CASES = [
    ("What is ROIC?", "roic"),
    ("Explain EVA.", "eva"),
    ("What is WACC?", "wacc"),
    ("Explain DCF valuation.", "dcf"),
    ("What is an LBO?", "lbo"),
    ("Explain SOTP valuation.", "sotp"),
    ("What is the PEG ratio?", "peg"),
    ("Explain the P/E ratio.", "p_e"),
    ("What is P/B?", "p_b"),
    ("What is EV/EBITDA?", "ev_ebitda"),
    ("What is EV/Sales?", "ev_sales"),
    ("Explain NOPAT.", "nopat"),
    ("What is NIM?", "nim"),
    ("Explain CASA.", "casa"),
    ("What is GNPA?", "gnpa"),
    ("Explain NNPA.", "nnpa"),
    ("What is CET1?", "cet1"),
    ("Explain the DuPont Model.", "dupont_model"),
    ("What is Free Cash Flow?", "free_cash_flow"),
    ("Explain FCF Yield.", "fcf_yield"),
    ("What is IRR?", "irr"),
    ("Explain NPV.", "npv"),
    ("What is TAM?", "total_addressable_market"),
    ("Explain DSCR.", "debt_service_coverage"),
    ("What is the Efficient Market Hypothesis?", "efficient_market_hypothesis"),
    ("Explain economic moat.", "economic_moat"),
    ("What are network effects?", "network_effect"),
    ("Explain switching costs.", "switching_cost"),
    ("What creates pricing power?", "pricing_power"),
    ("Explain CROCI.", "croci"),
    ("What is ROTE?", "rote"),
    ("Explain a QIP.", "qip"),
]


@pytest.mark.parametrize("question,expected_key", ALIAS_CASES)
def test_alias_and_phrasing_resolves_to_expected_key(question, expected_key):
    result = explain(question)
    assert result["found"], f"Failed to resolve: {question!r}"
    assert result["key"] == expected_key, f"{question!r} resolved to {result['key']!r}, expected {expected_key!r}"


def test_exact_key_lookup():
    result = explain("enterprise_value")
    assert result["found"]
    assert result["key"] == "enterprise_value"


def test_unknown_topic_returns_not_found():
    result = explain("the weather forecast for tomorrow")
    assert result["found"] is False


def test_empty_topic_returns_not_found():
    assert explain("")["found"] is False
    assert explain(None)["found"] is False


def test_search_ranks_relevant_concepts_first():
    results = search("enterprise value net debt", limit=3)
    assert results
    keys = [r["key"] for r in results]
    assert "enterprise_value" in keys or "net_debt" in keys


def test_search_empty_query_returns_empty():
    assert search("") == []


def test_search_respects_limit():
    results = search("capital return leverage margin", limit=2)
    assert len(results) <= 2


def test_operating_leverage_mentions_airlines():
    result = explain("Explain operating leverage using airlines.")
    assert result["found"]
    assert result["key"] == "operating_leverage"
    assert "airlin" in result["business_meaning"].lower()


def test_compound_key_phrase_beats_short_alias_substring():
    """Regression test: 'Explain Incremental ROIC' must resolve to
    incremental_roic, not the generic roic card. A single-word alias like
    'roic' is a subset of the question's words and must not win over a
    more specific, literally-present multi-word key phrase — found via the
    Concept Acceptance Test v1.0 (CA-10) before this fix."""

    result = explain("Explain Incremental ROIC.")
    assert result["found"]
    assert result["key"] == "incremental_roic"


def test_compound_key_phrase_priority_does_not_break_plain_roic():
    result = explain("Explain ROIC.")
    assert result["found"]
    assert result["key"] == "roic"


@pytest.mark.parametrize(
    "question,expected_key",
    [
        ("What is Incremental ROIC?", "incremental_roic"),
        ("Explain ROA decomposition.", "roa_decomposition"),
        ("Explain ROE decomposition.", "roe_decomposition"),
        ("What is Unlevered Beta?", "unlevered_beta"),
        ("What is Levered Beta?", "levered_beta"),
        ("Explain Free Cash Flow Yield.", "fcf_yield"),
        ("What is Unlevered Free Cash Flow?", "unlevered_fcf"),
        ("What is Levered Free Cash Flow?", "levered_fcf"),
    ],
)
def test_compound_keys_resolve_precisely_over_shorter_substrings(question, expected_key):
    result = explain(question)
    assert result["found"]
    assert result["key"] == expected_key
