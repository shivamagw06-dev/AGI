"""A value wrong by a million, and the evidence for saying so."""

from __future__ import annotations

import os
import tempfile

import pytest

os.environ.setdefault("INSTITUTIONAL_WAREHOUSE_ROOT", tempfile.mkdtemp(prefix="vp_"))

from institutional_warehouse import db, scale_guard  # noqa: E402
from institutional_warehouse import value_plausibility as vp  # noqa: E402

TAB = "financials_annual"


@pytest.fixture(autouse=True)
def fresh(tmp_path, monkeypatch):
    monkeypatch.setenv("INSTITUTIONAL_WAREHOUSE_ROOT", str(tmp_path))
    db.reset_backend()
    db.init(force=True)
    yield
    db.reset_backend()


def _seed(rows):
    for i, row in enumerate(rows):
        db.execute(
            f"INSERT INTO {db.physical_table(TAB)} (row_id, symbol, statement_type,"
            f" fiscal_year, revenue, source, sys_published, sys_reported_unit,"
            f" sys_unit_method) VALUES (?,?,?,?,?,?,1,?,?)",
            (f"r{i}", row.get("symbol", "ACME"), row.get("type", "CONSOLIDATED"),
             row.get("fy", "FY2024"), row.get("revenue"), row.get("source", "x"),
             row.get("unit"), row.get("method")))


def test_a_million_fold_peer_is_reported_even_when_the_size_looks_fine():
    """The ratio signal exists for values too small to look wrong."""
    _seed([{"revenue": 5000.0, "type": "CONSOLIDATED"},
           {"revenue": 5000.0 * 1e6, "type": "STANDALONE"}])
    out = vp.census(TAB)
    assert out["totals"]["ratio_corroborated"] == 1
    assert out["totals"]["rows_to_examine"] == 1


def test_a_tenfold_difference_is_left_alone():
    """Consolidated really can be ten times standalone. That is not a defect."""
    _seed([{"revenue": 5000.0, "type": "CONSOLIDATED"},
           {"revenue": 50000.0, "type": "STANDALONE"}])
    assert vp.census(TAB)["totals"]["rows_to_examine"] == 0


def test_two_signals_agreeing_is_reported_as_higher_confidence():
    _seed([{"revenue": 5000.0, "type": "CONSOLIDATED"},
           {"revenue": 5000.0 * 1e6, "type": "STANDALONE"}])
    out = vp.census(TAB)
    assert out["totals"]["two_signals_agree"] == 1
    assert out["sample"][0]["confidence"] == "two_signals"


def test_a_lone_impossible_row_is_reported_as_the_weaker_finding():
    """Most of the quarterly tab is in this state: no peer to compare against."""
    _seed([{"revenue": 9.5e9}])
    out = vp.census(TAB)
    assert out["totals"]["magnitude_only"] == 1
    assert out["totals"]["ratio_corroborated"] == 0
    assert out["sample"][0]["confidence"] == "magnitude_only"


def test_period_spellings_are_folded_before_anything_is_compared():
    """Without folding there is nothing to compare and the ratio signal is blind."""
    _seed([{"revenue": 5000.0, "fy": "FY2024", "type": "CONSOLIDATED"},
           {"revenue": 5000.0 * 1e6, "fy": "FY24", "type": "STANDALONE"}])
    assert vp.census(TAB)["totals"]["ratio_corroborated"] == 1


def test_the_census_writes_nothing():
    _seed([{"revenue": 9.5e9}])
    before = db.query(f"SELECT * FROM {db.physical_table(TAB)}")
    vp.census(TAB)
    vp.manifest(TAB)
    assert db.query(f"SELECT * FROM {db.physical_table(TAB)}") == before


def test_the_manifest_names_every_suspect_row():
    _seed([{"revenue": 9.5e9}, {"revenue": 8.1e9, "fy": "FY2023"}, {"revenue": 500.0,
                                                                    "fy": "FY2022"}])
    out = vp.manifest(TAB)
    assert out["rows_to_examine"] == 2
    assert {r["row_id"] for r in out["rows"]} == {"r0", "r1"}
    assert all(r["fields"] for r in out["rows"]), "a row is named with its evidence"


def test_per_share_columns_are_never_scale_tested():
    """eps and book_value are not aggregates; a scale test on them is meaningless."""
    assert "eps" not in vp.MONEY_FIELDS
    assert "book_value" not in vp.MONEY_FIELDS
    assert "shares_outstanding" not in vp.MONEY_FIELDS


# --- the guard ------------------------------------------------------------

def test_the_guard_is_off_by_default_and_changes_nothing():
    rows = [{"symbol": "ACME", "revenue": 9.5e9}]
    out = scale_guard.inspect(TAB, rows, source="financial_connector")
    assert out["mode"] == scale_guard.MODE_OFF
    assert out["keep"] == rows and out["isolate"] == []


def test_report_mode_counts_without_holding_anything_back():
    rows = [{"symbol": "ACME", "revenue": 9.5e9}]
    out = scale_guard.inspect(TAB, rows, source="financial_connector",
                              mode=scale_guard.MODE_REPORT)
    assert out["would_isolate"] == 1
    assert out["keep"] == rows and out["isolate"] == []


def test_isolate_mode_holds_the_row_back_and_says_why():
    rows = [{"symbol": "ACME", "revenue": 9.5e9}, {"symbol": "ACME", "revenue": 5000.0}]
    out = scale_guard.inspect(TAB, rows, source="financial_connector",
                              mode=scale_guard.MODE_ISOLATE)
    assert len(out["isolate"]) == 1 and len(out["keep"]) == 1
    finding = out["findings"][0]
    assert finding["fields"] == ["revenue"]
    assert finding["source_unit_documented"] is False, \
        "an undocumented source is the condition that caused this defect"


def test_the_guard_notes_when_the_source_does_have_a_documented_unit():
    out = scale_guard.inspect(TAB, [{"symbol": "ACME", "revenue": 9.5e9}],
                              source="capital_iq_workbook",
                              mode=scale_guard.MODE_ISOLATE)
    assert out["findings"][0]["source_unit_documented"] is True
    assert out["findings"][0]["documented_unit"] == "inr_million"


# --- failing closed on an undocumented unit -------------------------------

def test_an_undocumented_source_is_not_treated_as_canonical():
    """The defect, stated as a rule.

    earnings_intelligence_p21 and financial_connector have no documented unit.
    resolve_unit treats that as "already INR million", which is how raw rupees
    reached a millions column. Neither can be given a default instead: both are
    non-uniform, so a default would corrupt the rows already in millions.
    """
    assert scale_guard.source_unit_is_documented("earnings_intelligence_p21") is False
    assert scale_guard.source_unit_is_documented("financial_connector") is False
    assert scale_guard.source_unit_is_documented("capital_iq_workbook") is True


def test_fail_closed_holds_an_ordinary_looking_row_from_an_unknown_source():
    rows = [{"symbol": "ACME", "revenue": 5000.0}]
    out = scale_guard.inspect(TAB, rows, source="financial_connector",
                              mode=scale_guard.MODE_ISOLATE,
                              fail_closed_on_unknown_unit=True)
    assert len(out["isolate"]) == 1
    assert out["findings"][0]["reason"].startswith("source has no documented unit")


def test_fail_closed_leaves_documented_sources_alone():
    rows = [{"symbol": "ACME", "revenue": 5000.0}]
    out = scale_guard.inspect(TAB, rows, source="capital_iq_workbook",
                              mode=scale_guard.MODE_ISOLATE,
                              fail_closed_on_unknown_unit=True)
    assert out["keep"] == rows and out["isolate"] == []


def test_fail_closed_is_opt_in_and_off_by_default():
    rows = [{"symbol": "ACME", "revenue": 5000.0}]
    out = scale_guard.inspect(TAB, rows, source="financial_connector",
                              mode=scale_guard.MODE_ISOLATE)
    assert out["keep"] == rows and out["isolate"] == []
