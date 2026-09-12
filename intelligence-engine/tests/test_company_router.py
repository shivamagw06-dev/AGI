"""IKT Company Router — routes company-shaped questions to bulk-uploaded
Institutional Knowledge Tables data (Capital IQ-style screener exports).

Uses an isolated IKT_STORE_ROOT so this suite never depends on (or
pollutes) any real bulk-uploaded dataset.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ["IKT_STORE_ROOT"] = "/tmp/ikt_company_router_test_store"

import pytest

from institutional_knowledge_tables.store import delete_company, upsert_fact
from app.ui.company_router import (
    answer_company_profile,
    detect_ikt_company,
    invalidate_index_cache,
    route,
)

_TEST_TICKERS = ("TESTCO", "BSE999999", "TESTMULTI")


def setup_function():
    for t in _TEST_TICKERS:
        delete_company(t)
    invalidate_index_cache()


def _seed_testco():
    upsert_fact("TESTCO", "company_master", "company_name", "Testco Widgets Limited", source="test")
    upsert_fact("TESTCO", "company_master", "sector", "Industrials", source="test")
    upsert_fact("TESTCO", "company_master", "industry", "Widget Manufacturing", source="test")
    upsert_fact("TESTCO", "company_master", "country", "India", source="test")
    upsert_fact("TESTCO", "company_master", "company_type", "Public Company", source="test")
    upsert_fact(
        "TESTCO", "business_model", "description",
        "Testco Widgets Limited manufactures and sells precision widgets. It operates in India and exports internationally.",
        source="test",
    )
    upsert_fact("TESTCO", "competitors", "peer", "Acme Widgets Ltd; Global Gadgets Inc", source="test")
    upsert_fact("TESTCO", "market_data", "market_cap", 5000.0, source="test", period="latest")
    upsert_fact("TESTCO", "financial_statements", "revenue", 800.0, source="test", period="LTM")
    invalidate_index_cache()


def test_detects_company_by_full_name():
    _seed_testco()
    assert detect_ikt_company("What is Testco Widgets Limited's business model?") == "TESTCO"


def test_detects_company_by_partial_name():
    _seed_testco()
    assert detect_ikt_company("Explain Testco Widgets.") == "TESTCO"


def test_detects_company_by_ticker_token():
    _seed_testco()
    assert detect_ikt_company("Tell me about TESTCO.") == "TESTCO"


def test_bse_style_ticker_also_detected():
    upsert_fact("BSE999999", "company_master", "company_name", "Nineties Nostalgia Limited", source="test")
    upsert_fact(
        "BSE999999", "business_model", "description",
        "Nineties Nostalgia Limited sells retro merchandise across India.", source="test",
    )
    invalidate_index_cache()
    assert detect_ikt_company("Explain Nineties Nostalgia Limited.") == "BSE999999"


def test_no_false_positive_for_unrelated_question():
    _seed_testco()
    assert detect_ikt_company("What is Free Cash Flow?") is None
    assert detect_ikt_company("Should I buy HDFC Bank tomorrow?") is None
    assert detect_ikt_company("Explain XYZ Quantum Robotics Pvt Ltd.") is None


def test_no_company_matched_when_store_empty():
    invalidate_index_cache()
    assert detect_ikt_company("What is Testco Widgets Limited's business model?") is None


def test_answer_uses_only_real_ikt_data():
    _seed_testco()
    result = route("What is Testco Widgets Limited's business model?")
    assert result is not None
    assert result["engine"] == "institutional_knowledge_tables"
    assert result["key"] == "TESTCO"
    assert "widgets" in result["summary"].lower()
    assert result["evidence"]


def test_answer_includes_sector_market_cap_and_competitors_in_why():
    _seed_testco()
    result = route("Explain Testco Widgets Limited.")
    why_text = " ".join(result["why"]).lower()
    assert "industrials" in why_text
    assert "5000" in why_text or "market cap" in why_text.lower()
    assert "acme widgets" in why_text


def test_no_answer_when_company_has_no_business_content():
    """A company with only a bare ticker/name and no sector or description
    must not produce a fabricated profile."""

    upsert_fact("TESTMULTI", "company_master", "company_name", "Empty Shell Holdings Limited", source="test")
    invalidate_index_cache()
    result = answer_company_profile("TESTMULTI", "Explain Empty Shell Holdings Limited.")
    assert result is None


def test_route_returns_none_for_unknown_ticker():
    assert answer_company_profile("NOT_A_REAL_TICKER_XYZ", "irrelevant") is None


def test_index_cache_refreshes_after_invalidate():
    invalidate_index_cache()
    assert detect_ikt_company("Explain Testco Widgets Limited.") is None
    _seed_testco()
    assert detect_ikt_company("Explain Testco Widgets Limited.") == "TESTCO"


@pytest.mark.parametrize(
    "question",
    [
        "What creates pricing power?",
        "Explain the DuPont model.",
        "Founder invests ₹1 crore. Build the journal entry and opening balance sheet.",
        "Why does every transaction require a debit and a credit?",
    ],
)
def test_concept_and_accounting_questions_never_match_a_company(question):
    _seed_testco()
    assert detect_ikt_company(question) is None
