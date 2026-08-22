"""Trusted and unverified quarterly data, kept apart on read."""

from __future__ import annotations

import pytest

from institutional_warehouse import statement_trust as st

QT = "financials_quarterly"
AN = "financials_annual"


def row(source, method="declared", symbol="ACME", **kw):
    return {"symbol": symbol, "source": source, "sys_unit_method": method,
            "fiscal_period": "FY2027Q1", "revenue": 1000.0, **kw}


# --- what counts as trusted ------------------------------------------------

@pytest.mark.parametrize("source", ["upstox", "upstox_fundamentals"])
def test_a_declared_upstox_row_is_trusted(source):
    assert st.is_trusted(QT, row(source)) is True
    assert st.classify(QT, row(source)) == st.TRUSTED


@pytest.mark.parametrize("source", [
    "yahoo_finance_statements", "financial_connector",
    "earnings_intelligence_p21", "formula_engine",
])
def test_every_undeclared_feed_is_fallback(source):
    assert st.is_trusted(QT, row(source, "assumed_canonical")) is False
    assert st.classify(QT, row(source, "assumed_canonical")) == st.FALLBACK


def test_a_trusted_source_without_a_declared_unit_is_not_trusted():
    """Both conditions, not either.

    assumed_canonical is the absence of a unit wearing the name of one, and a
    trusted feed can still fail to declare on a given row.
    """
    assert st.is_trusted(QT, row("upstox", "assumed_canonical")) is False


def test_a_missing_unit_method_is_not_trusted():
    assert st.is_trusted(QT, row("upstox", None)) is False


def test_unit_method_is_read_from_meta_when_not_on_the_row():
    """Warehouse reads return it under _meta; writes carry it on the row."""
    r = {"symbol": "ACME", "source": "upstox", "_meta": {"unit_method": "declared"}}
    assert st.is_trusted(QT, r) is True


# --- default reads ---------------------------------------------------------

def test_default_reads_return_trusted_only():
    rows = [row("upstox"), row("yahoo_finance_statements", "assumed_canonical")]
    out = st.select(QT, rows)
    assert len(out) == 1 and out[0]["source"] == "upstox"


def test_fallback_requires_an_explicit_opt_in():
    rows = [row("upstox"), row("yahoo_finance_statements", "assumed_canonical")]
    out = st.select(QT, rows, include_unverified=True)
    assert len(out) == 2
    assert [r.get("trust") for r in out][1] == st.FALLBACK


def test_trusted_rows_come_first_when_fallback_is_included():
    """A caller taking the first row per period gets the declared one."""
    rows = [row("yahoo_finance_statements", "assumed_canonical"), row("upstox")]
    out = st.select(QT, rows, include_unverified=True)
    assert out[0]["source"] == "upstox"


def test_nothing_is_dropped_by_partition():
    rows = [row("upstox"), row("formula_engine", "assumed_canonical"),
            row("financial_connector", None)]
    trusted, fallback = st.partition(QT, rows)
    assert len(trusted) + len(fallback) == 3


def test_labelling_filters_nothing():
    rows = [row("upstox"), row("yahoo_finance_statements", "assumed_canonical")]
    out = st.label(QT, rows)
    assert len(out) == 2
    assert {r["trust"] for r in out} == {st.TRUSTED, st.FALLBACK}


# --- coverage is stated, not implied --------------------------------------

def test_coverage_reports_what_a_reader_actually_gets():
    rows = ([row("upstox", symbol=f"T{i}") for i in range(3)]
            + [row("yahoo_finance_statements", "assumed_canonical", symbol=f"F{i}")
               for i in range(7)])
    cov = st.coverage(QT, rows)
    assert cov["trusted_companies"] == 3
    assert cov["fallback_only_companies"] == 7
    assert "excluded from valuations" in cov["note"]


# --- annual is governed separately ----------------------------------------

def test_the_capital_iq_workbook_is_trusted_for_annual():
    assert st.is_trusted(AN, row("capital_iq_workbook", "source_default")) is True


def test_annual_trust_does_not_change_the_quarterly_rule():
    """capital_iq_workbook is not a quarterly source; upstox is not the annual owner."""
    assert st.is_trusted(QT, row("capital_iq_workbook", "declared")) is False
    assert "capital_iq_workbook" not in st.TRUSTED_QUARTERLY_SOURCES


def test_an_unknown_tab_trusts_nothing():
    assert st.trusted_sources("daily_market_history") == frozenset()
    assert st.is_trusted("daily_market_history", row("upstox")) is False
