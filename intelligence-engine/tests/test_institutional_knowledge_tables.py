"""IKT-01 — versioned fact store. Never overwrite history; never fabricate."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import os

os.environ.setdefault("IKT_STORE_ROOT", "/tmp/ikt_test_store")

from institutional_knowledge_tables.store import (
    company_record,
    delete_company,
    get_field_history,
    get_table,
    upsert_fact,
)


def setup_function():
    delete_company("TESTCO")


def test_upsert_creates_first_version():
    meta = upsert_fact(
        "TESTCO", "management", "ceo", "A. Kumar", source="Annual Report FY25"
    )
    assert meta["version"] == 1
    hist = get_field_history("TESTCO", "management", "ceo")
    assert len(hist) == 1
    assert hist[0]["current"] is True
    assert hist[0]["value"] == "A. Kumar"


def test_second_upsert_versions_not_overwrites():
    upsert_fact("TESTCO", "management", "ceo", "A. Kumar", source="Annual Report FY25")
    upsert_fact("TESTCO", "management", "ceo", "B. Singh", source="Annual Report FY26")
    hist = get_field_history("TESTCO", "management", "ceo")
    assert len(hist) == 2
    assert hist[0]["current"] is False
    assert hist[0]["value"] == "A. Kumar"
    assert hist[1]["current"] is True
    assert hist[1]["value"] == "B. Singh"

    table = get_table("TESTCO", "management")
    assert table["row"]["ceo"]["value"] == "B. Singh"
    assert table["row"]["ceo"]["version"] == 2


def test_missing_field_stays_null_not_fabricated():
    upsert_fact("TESTCO", "management", "ceo", "A. Kumar", source="Annual Report FY25")
    table = get_table("TESTCO", "management")
    assert table["row"]["cfo"] is None
    assert "cfo" in table["missing_fields"]
    assert table["coverage_pct"] < 100.0


def test_period_keyed_table_versions_within_period():
    upsert_fact(
        "TESTCO",
        "financial_statements",
        "revenue",
        75000,
        source="Investor Presentation Q1FY27",
        period="FY2027-Q1",
    )
    upsert_fact(
        "TESTCO",
        "financial_statements",
        "revenue",
        82000,
        source="Annual Report FY27",
        period="FY2027-Q1",
    )
    hist = get_field_history("TESTCO", "financial_statements", "revenue", period="FY2027-Q1")
    assert len(hist) == 2
    assert hist[-1]["value"] == 82000
    assert hist[-1]["current"] is True
    assert hist[0]["current"] is False

    table = get_table("TESTCO", "financial_statements", period="FY2027-Q1")
    assert table["row"]["revenue"]["value"] == 82000

    # A different period is independent — no cross-period bleed
    other = get_table("TESTCO", "financial_statements", period="FY2026-Q4")
    assert other["found"] is False


def test_unknown_table_and_field_rejected():
    try:
        upsert_fact("TESTCO", "not_a_table", "x", 1, source="test")
        assert False, "should have raised"
    except ValueError:
        pass
    try:
        upsert_fact("TESTCO", "company_master", "not_a_field", 1, source="test")
        assert False, "should have raised"
    except ValueError:
        pass


def test_source_required_no_fabrication():
    try:
        upsert_fact("TESTCO", "management", "ceo", "Nobody", source="")
        assert False, "should have raised without a source"
    except ValueError:
        pass


def test_company_record_reports_only_populated_tables():
    upsert_fact("TESTCO", "management", "ceo", "A. Kumar", source="Annual Report FY25")
    rec = company_record("TESTCO")
    assert rec["populated_tables"] == ["management"]
    assert rec["total_tables"] == 24
