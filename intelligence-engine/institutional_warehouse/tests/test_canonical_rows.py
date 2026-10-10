"""Canonical fundamentals rows, tested on the defect that produced them.

RELIANCE's June 2026 quarter was stored four times, in three magnitudes, under
four labels. Upstox sent crores and they were rescaled to INR million; another
importer sent absolute rupees, declared no unit, and 1,660,130,000,000 was
stored as though it were already millions. Nothing was overwritten and no check
failed - there was simply no rule about which of the four a reader should
believe.

These are the failures that rule has to make impossible.
"""

from __future__ import annotations

import os
import tempfile

import pytest

os.environ.setdefault("INSTITUTIONAL_WAREHOUSE_ROOT", tempfile.mkdtemp(prefix="wh_canon_"))

from institutional_warehouse import (  # noqa: E402
    canonical_rows, db, gateway, period_identity, store,
)

TAB = "financials_quarterly"


@pytest.fixture(autouse=True)
def fresh(tmp_path, monkeypatch):
    monkeypatch.setenv("INSTITUTIONAL_WAREHOUSE_ROOT", str(tmp_path))
    db.reset_backend()
    db.init(force=True)
    yield
    db.reset_backend()


def _row(**over):
    row = {"symbol": "RELIANCE", "statement_type": "CONSOLIDATED",
           "fiscal_period": "FY2027Q1", "revenue": 3160180.0}
    row.update(over)
    return row


def _stored(symbol="RELIANCE"):
    return [r for r in store.all_rows(TAB) if r.get("symbol") == symbol]


# --------------------------------------------------------------------------
# One identity for a period, whatever the vendor called it
# --------------------------------------------------------------------------

@pytest.mark.parametrize("label", ["Q1 FY27", "FY27Q1", "FY2027Q1", "Jun 2026",
                                   "2026-06-30", "2026-07-01"])
def test_every_spelling_of_one_quarter_shares_a_key(label):
    """The four live spellings plus the two date forms are one period."""
    assert period_identity.period_key(label) == "2026-07-01"


def test_two_digit_and_four_digit_fiscal_years_are_one_year():
    """FY26 against FY2026 is the pair that forked the annual tab."""
    assert period_identity.period_key("FY26") == period_identity.period_key("FY2026")


def test_quarter_one_of_a_fiscal_year_is_the_june_quarter_before_it():
    """Indian fiscal years end in March, so FY2027 Q1 is June *2026*."""
    assert period_identity.canonical_label("Q1 FY27", tab_id=TAB) == "FY2027Q1"
    assert period_identity.period_key("Q1 FY27").startswith("2026-")


def test_a_non_march_quarter_gets_no_invented_quarter_number():
    """A company off the March calendar has no standard fiscal quarter.

    Guessing one would file a real result under a label meaning other months.
    """
    assert period_identity.canonical_label("May 2026", tab_id=TAB) is None
    assert period_identity.period_key("May 2026") == "2026-06-01"


# --------------------------------------------------------------------------
# Who may write a canonical row
# --------------------------------------------------------------------------

def test_yahoo_cannot_write_a_canonical_quarterly_row():
    """The central rule. Yahoo may write; its rows are not the answer."""
    result = gateway.write(TAB, [_row()], source="yahoo_finance_statements",
                           actor="test", reason="test")
    assert result["ok"] is True, "evidence is kept, not rejected"
    rows = _stored()
    assert len(rows) == 1
    assert not rows[0]["is_canonical"]
    assert canonical_rows.SOURCE_NOT_CANONICAL in rows[0]["canonical_blockers"]


def test_financial_connector_cannot_write_a_canonical_quarterly_row():
    result = gateway.write(TAB, [_row(revenue=1660130000000.0)],
                           source="financial_connector", actor="test", reason="test")
    assert result["ok"] is True
    assert not _stored()[0]["is_canonical"]


def test_a_non_owner_claiming_canonical_is_rejected_outright():
    """Asserting the flag is appointing yourself the authority, not a preference."""
    result = gateway.write(TAB, [_row(is_canonical=True)],
                           source="yahoo_finance_statements", actor="test", reason="test")
    assert result["ok"] is False
    assert result["error"] == "ownership_violation"
    assert any(v["rule"] == "canonical_claim_not_owned" for v in result["violations"])
    assert _stored() == [], "a rejected write lands nothing"


def test_upstox_writes_a_canonical_row_when_everything_is_known():
    result = gateway.write(TAB, [_row()], source="upstox", actor="test",
                           reason="test", reported_unit="crore")
    assert result["ok"] is True
    rows = _stored()
    assert rows[0]["is_canonical"]
    assert not rows[0]["canonical_blockers"]
    assert rows[0]["period_key"] == "2026-07-01"


def test_capital_iq_is_canonical_for_deep_history():
    gateway.write("financials_annual", [{"symbol": "RELIANCE", "fiscal_year": "FY2016",
                                         "statement_type": "CONSOLIDATED", "revenue": 100.0}],
                  source="capital_iq_workbook", actor="test", reason="test",
                  reported_unit="inr_million")
    rows = [r for r in store.all_rows("financials_annual") if r.get("symbol") == "RELIANCE"]
    assert rows[0]["is_canonical"]


# --------------------------------------------------------------------------
# The four things that must be known
# --------------------------------------------------------------------------

def test_an_unknown_statement_type_is_not_canonical():
    """UNKNOWN cannot be compared against its own sibling, so it is not an answer."""
    gateway.write(TAB, [_row(statement_type="UNKNOWN")], source="upstox",
                  actor="test", reason="test", reported_unit="crore")
    row = _stored()[0]
    assert not row["is_canonical"]
    assert canonical_rows.STATEMENT_TYPE_UNKNOWN in row["canonical_blockers"]


def test_a_missing_statement_type_is_not_canonical():
    """A row that declares nothing is filled with UNKNOWN, which is still unknown."""
    gateway.write(TAB, [_row(statement_type=None)], source="upstox",
                  actor="test", reason="test", reported_unit="crore")
    assert not _stored()[0]["is_canonical"]


def test_an_unparseable_period_is_not_canonical():
    gateway.write(TAB, [_row(fiscal_period="Q1")], source="upstox",
                  actor="test", reason="test", reported_unit="crore")
    row = _stored()[0]
    assert not row["is_canonical"]
    assert canonical_rows.PERIOD_UNPARSEABLE in row["canonical_blockers"]


def test_an_assumed_unit_is_not_a_known_unit():
    """The exact failure that put absolute rupees in a column of INR million.

    An unrecognised source declaring nothing falls through to "assume it is
    already canonical". That assumption may not produce a canonical row.
    """
    gateway.write(TAB, [_row()], source="some_new_vendor", actor="test", reason="test")
    row = _stored()[0]
    assert not row["is_canonical"]
    assert canonical_rows.UNITS_UNKNOWN in row["canonical_blockers"]


# --------------------------------------------------------------------------
# Protecting a row that is already the answer
# --------------------------------------------------------------------------

def test_a_non_canonical_row_cannot_overwrite_a_canonical_one():
    """Arriving later is not an argument."""
    gateway.write(TAB, [_row(revenue=3160180.0)], source="upstox", actor="test",
                  reason="test", reported_unit="crore")
    before = _stored()[0]["revenue"]

    result = gateway.write(TAB, [_row(revenue=999.0)], source="yahoo_finance_statements",
                           actor="test", reason="test")
    assert result.get("refused_downgrade") == 1
    assert _stored()[0]["revenue"] == before
    assert _stored()[0]["is_canonical"]


def test_a_canonical_row_may_still_be_updated_by_a_canonical_source():
    """The guard protects against downgrade, not against a genuine restatement."""
    gateway.write(TAB, [_row(revenue=3160180.0)], source="upstox", actor="test",
                  reason="test", reported_unit="crore")
    gateway.write(TAB, [_row(revenue=3200000.0)], source="upstox", actor="test",
                  reason="restated", reported_unit="crore")
    rows = _stored()
    assert len(rows) == 1, "a restatement is a new version of one row, not a second row"
    assert rows[0]["revenue"] == pytest.approx(3200000.0 * 10)


def test_a_row_of_unknown_magnitude_cannot_overwrite_one_of_known_magnitude():
    """The rupees-into-a-millions-column defect, stated as a test.

    The stored value has been rescaled into INR million. The incoming one is in
    whatever its vendor sent, because nobody knows what that is. Writing the
    second over the first is not an update.
    """
    # Stored with a known unit but not canonical, so the downgrade rule - which
    # would otherwise catch this first - does not apply and the unit rule is
    # what is actually under test.
    gateway.write(TAB, [_row(statement_type="UNKNOWN")], source="upstox",
                  actor="test", reason="test", reported_unit="crore")
    before = _stored()[0]["revenue"]

    result = gateway.write(TAB, [_row(statement_type="UNKNOWN", revenue=1660130000000.0)],
                           source="some_new_vendor", actor="test", reason="test")
    assert result.get("refused_unknown_units") == 1
    assert _stored()[0]["revenue"] == before


def test_a_non_canonical_row_is_refused_before_its_units_are_even_considered():
    """Two rules protect a canonical row; the stricter one fires first."""
    gateway.write(TAB, [_row()], source="upstox", actor="test", reason="test",
                  reported_unit="crore")
    result = gateway.write(TAB, [_row(revenue=1660130000000.0)],
                           source="some_new_vendor", actor="test", reason="test")
    assert result.get("refused_downgrade") == 1
    assert _stored()[0]["revenue"] == pytest.approx(3160180.0 * 10)


def test_a_known_magnitude_may_replace_an_assumed_one():
    """The other direction is the repair, not the corruption."""
    gateway.write(TAB, [_row(revenue=1660130000000.0)], source="some_new_vendor",
                  actor="test", reason="test")
    gateway.write(TAB, [_row(revenue=3160180.0)], source="upstox", actor="test",
                  reason="test", reported_unit="crore")
    row = _stored()[0]
    assert row["revenue"] == pytest.approx(3160180.0 * 10)
    assert row["is_canonical"]


def test_two_input_scales_normalised_to_the_same_storage_scale_are_compatible():
    """Crore against inr_million is what normalisation is for, not a conflict."""
    gateway.write(TAB, [_row(revenue=100.0)], source="capital_iq_workbook",
                  actor="test", reason="test")
    result = gateway.write(TAB, [_row(revenue=50.0)], source="upstox", actor="test",
                           reason="test", reported_unit="crore")
    assert not result.get("refused_unknown_units")
    assert _stored()[0]["revenue"] == pytest.approx(500.0)


# --------------------------------------------------------------------------
# Labels, and what may not be rewritten
# --------------------------------------------------------------------------

def test_a_canonical_source_writes_one_spelling():
    """Upstox sending Jun 2026 is stored as FY2027Q1, so the next write finds it."""
    gateway.write(TAB, [_row(fiscal_period="Jun 2026")], source="upstox",
                  actor="test", reason="test", reported_unit="crore")
    assert _stored()[0]["fiscal_period"] == "FY2027Q1"


def test_a_legacy_source_is_normalised_too_so_it_can_still_be_seen_to_disagree():
    """Every write is normalised, not only the trusted ones.

    Normalising only canonical sources looks safer and is worse: the two rows
    stop sharing an identity, so they never collide, and a disagreement between
    Upstox and Yahoo can never be recorded. Sources share a row here by design.
    """
    gateway.write(TAB, [_row(fiscal_period="Q1 FY27")],
                  source="yahoo_finance_statements", actor="test", reason="test")
    row = _stored()[0]
    assert row["fiscal_period"] == "FY2027Q1"
    assert row["period_key"] == "2026-07-01"


def test_two_sources_disagreeing_about_one_quarter_land_on_one_row():
    """The duplication defect, stated as a test."""
    gateway.write(TAB, [_row(fiscal_period="Jun 2026", revenue=3160180.0)],
                  source="upstox", actor="test", reason="test", reported_unit="crore")
    gateway.write(TAB, [_row(fiscal_period="Q1 FY27", revenue=3094680.0)],
                  source="yahoo_finance_statements", actor="test", reason="test")
    assert len(_stored()) == 1, "one quarter is one row, whatever it was called"


def test_two_spellings_from_one_canonical_source_collapse_to_one_row():
    """The defect, stated as a test: this used to produce two rows."""
    gateway.write(TAB, [_row(fiscal_period="Jun 2026")], source="upstox",
                  actor="test", reason="test", reported_unit="crore")
    gateway.write(TAB, [_row(fiscal_period="Q1 FY27")], source="upstox",
                  actor="test", reason="test", reported_unit="crore")
    rows = _stored()
    assert len(rows) == 1
    assert rows[0]["fiscal_period"] == "FY2027Q1"
