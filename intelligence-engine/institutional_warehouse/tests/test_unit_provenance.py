"""Establishing a documented unit, without touching a single number.

The reconciliation dry run kept 55 of 68,866 annual rows because 47,474 Capital
IQ rows say inr_million and say nobody established it. This fixes the second
half of that sentence and must not touch the first.
"""

from __future__ import annotations

import os
import tempfile

import pytest

os.environ.setdefault("INSTITUTIONAL_WAREHOUSE_ROOT", tempfile.mkdtemp(prefix="up_"))

from institutional_warehouse import db, unit_provenance as up  # noqa: E402
from institutional_warehouse import reconciliation_inventory as inv  # noqa: E402

TAB = "financials_annual"


@pytest.fixture(autouse=True)
def fresh(tmp_path, monkeypatch):
    monkeypatch.setenv("INSTITUTIONAL_WAREHOUSE_ROOT", str(tmp_path))
    db.reset_backend()
    db.init(force=True)
    yield
    db.reset_backend()


def _seed(rows):
    for i, r in enumerate(rows):
        db.execute(
            f"INSERT INTO {db.physical_table(TAB)} (row_id, symbol, statement_type,"
            f" fiscal_year, revenue, source, sys_published, sys_reported_unit, sys_unit_method)"
            f" VALUES (?,?,?,?,?,?,1,?,?)",
            (f"r{i}", r.get("symbol", "AAA"), r.get("type", "CONSOLIDATED"),
             r.get("fy", "FY2020"), r.get("revenue", 100.0), r["source"],
             r.get("unit"), r.get("method")))


CAPIQ_ASSUMED = {"source": "capital_iq_workbook", "unit": "inr_million",
                 "method": "assumed_canonical"}


def test_it_targets_only_the_rows_it_says_it_does():
    _seed([
        CAPIQ_ASSUMED,                                                    # eligible
        {**CAPIQ_ASSUMED, "fy": "FY2021"},                                # eligible
        {**CAPIQ_ASSUMED, "fy": "FY2022", "method": "declared"},          # already known
        {**CAPIQ_ASSUMED, "fy": "FY2023", "unit": "crore"},               # different unit
        {"source": "yahoo_finance_statements", "unit": "inr_million",
         "method": "assumed_canonical", "fy": "FY2024"},                  # different source
        {"source": "financial_connector", "unit": None, "method": None,
         "fy": "FY2025"},                                                 # untouched
    ])
    out = up.plan(TAB)
    assert out["rows_eligible"] == 2
    assert out["rows_for_source_total"] == 4
    assert out["rows_left_alone"] == 2


def test_no_financial_value_is_read_or_written():
    _seed([CAPIQ_ASSUMED])
    before = db.query(f"SELECT revenue FROM {db.physical_table(TAB)}")[0]["revenue"]
    up.apply(TAB, actor="test", confirm=True)
    after = db.query(f"SELECT revenue FROM {db.physical_table(TAB)}")[0]["revenue"]
    assert after == before == 100.0


def test_it_refuses_without_an_explicit_confirmation():
    _seed([CAPIQ_ASSUMED])
    out = up.apply(TAB, actor="test")
    assert out["ok"] is False and out["error"] == "confirm_required"
    assert out["plan"]["rows_eligible"] == 1
    row = db.query(f"SELECT sys_unit_method AS m FROM {db.physical_table(TAB)}")[0]
    assert row["m"] == "assumed_canonical", "a refused apply must change nothing"


def test_running_it_twice_changes_nothing_the_second_time():
    _seed([CAPIQ_ASSUMED, {**CAPIQ_ASSUMED, "fy": "FY2021"}])
    first = up.apply(TAB, actor="test", confirm=True)
    second = up.apply(TAB, actor="test", confirm=True)
    assert first["changed"] == 2
    assert second["changed"] == 0 and second["already_done"] is True


def test_the_rollback_sql_puts_it_back():
    _seed([CAPIQ_ASSUMED, {**CAPIQ_ASSUMED, "fy": "FY2021"}])
    rollback = up.plan(TAB)["rollback_sql"]
    up.apply(TAB, actor="test", confirm=True)
    assert up.plan(TAB)["rows_eligible"] == 0

    for statement in [s for s in rollback.split("\n") if not s.startswith("--")]:
        db.execute(statement.rstrip(";"))
    assert up.plan(TAB)["rows_eligible"] == 2, "rollback must restore the prior state"


def test_the_plan_writes_nothing():
    _seed([CAPIQ_ASSUMED])
    up.plan(TAB)
    row = db.query(f"SELECT sys_unit_method AS m FROM {db.physical_table(TAB)}")[0]
    assert row["m"] == "assumed_canonical"


def test_the_simulation_matches_what_applying_it_actually_does():
    """The inventory's preview must not be a second description of the rule."""
    _seed([CAPIQ_ASSUMED, {**CAPIQ_ASSUMED, "fy": "FY2021"},
           {"source": "yahoo_finance_statements", "unit": "rupee",
            "method": "source_default", "fy": "FY2022"}])

    simulated = inv.inventory(TAB, simulate_unit_provenance=True)["totals"]
    up.apply(TAB, actor="test", confirm=True)
    real = inv.inventory(TAB)["totals"]

    for key in ("rows_with_unknown_units", "rows_that_survive", "manual_review_rows"):
        assert simulated[key] == real[key], f"{key} differs between simulation and reality"


def test_establishing_provenance_makes_those_rows_readable():
    """The point of the exercise, stated as a test."""
    _seed([CAPIQ_ASSUMED])
    before = inv.inventory(TAB)["totals"]
    after = inv.inventory(TAB, simulate_unit_provenance=True)["totals"]
    assert before["rows_that_survive"] == 0
    assert before["rows_with_unknown_units"] == 1
    assert after["rows_that_survive"] == 1
    assert after["rows_with_unknown_units"] == 0


def test_manual_review_counts_each_row_once():
    """It counted the annual tab at 137,617 of 68,866 rows - exactly twice."""
    _seed([{"source": "financial_connector", "unit": None, "method": None},
           {"source": "financial_connector", "unit": None, "method": None, "fy": "FY2021"},
           {"source": "yahoo_finance_statements", "unit": "rupee",
            "method": "source_default", "fy": "FY2022"}])
    totals = inv.inventory(TAB)["totals"]
    assert totals["manual_review_rows"] <= totals["rows"]
