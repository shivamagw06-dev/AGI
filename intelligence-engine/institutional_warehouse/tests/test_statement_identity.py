"""Financial statement identity.

The motivating defect: a consolidated and a standalone filing for one company
and year hashed to the same warehouse key, so the second import silently
replaced the first with no conflict and no history.
"""

from __future__ import annotations

import os
import tempfile

import pytest

os.environ.setdefault("INSTITUTIONAL_WAREHOUSE_ROOT", tempfile.mkdtemp(prefix="wh_ident_"))

from institutional_warehouse import db, gateway, statement_identity, store  # noqa: E402
from institutional_warehouse.schema import find_tab  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_warehouse(tmp_path, monkeypatch):
    monkeypatch.setenv("INSTITUTIONAL_WAREHOUSE_ROOT", str(tmp_path))
    db.reset_backend()
    db.init(force=True)
    yield
    db.reset_backend()


def _write(symbol, *, statement_type=None, revenue=1000.0, source="upstox_fundamentals",
           year="FY2025"):
    row = {"symbol": symbol, "fiscal_year": year, "revenue": revenue}
    if statement_type is not None:
        row["statement_type"] = statement_type
    return gateway.write("financials_annual", [row], source=source, actor="test")


# -- identity is part of the key -------------------------------------------


def test_statement_type_is_part_of_the_key():
    assert "statement_type" in find_tab("financials_annual").key
    assert "statement_type" in find_tab("financials_quarterly").key


def test_consolidated_and_standalone_coexist():
    _write("AAA", statement_type="CONSOLIDATED", revenue=1000.0)
    _write("AAA", statement_type="STANDALONE", revenue=600.0)

    rows = store.all_rows("financials_annual", entity="AAA")
    assert len(rows) == 2, "the second filing must not replace the first"
    by_type = {r["statement_type"]: r["revenue"] for r in rows}
    assert by_type["CONSOLIDATED"] == pytest.approx(10_000.0)  # 1,000 cr -> mn
    assert by_type["STANDALONE"] == pytest.approx(6_000.0)


def test_consolidated_and_standalone_are_never_compared():
    """Different facts, so a difference between them is not a disagreement."""
    _write("BBB", statement_type="CONSOLIDATED", revenue=1000.0,
           source="yahoo_finance_statements")
    result = _write("BBB", statement_type="STANDALONE", revenue=600.0,
                    source="upstox_fundamentals")
    assert result["conflicts"] == 0


def test_two_sources_on_one_identity_still_conflict():
    """Source is deliberately not in the key, so DQIV can still compare vendors."""
    _write("CCC", statement_type="CONSOLIDATED", revenue=45_800_000_000.0,
           source="yahoo_finance_statements")
    result = _write("CCC", statement_type="CONSOLIDATED", revenue=6_000.0,
                    source="upstox_fundamentals")
    assert result["conflicts"] == 1
    assert len(store.all_rows("financials_annual", entity="CCC")) == 1


# -- defaulting ------------------------------------------------------------


def test_a_collector_that_declares_no_type_still_lands():
    """Every existing collector predates this field; none may start dropping rows."""
    result = _write("DDD")
    assert result["written"] == 1
    row = store.all_rows("financials_annual", entity="DDD")[0]
    assert row["statement_type"] == "UNKNOWN"
    assert row["statement_frequency"] == "ANNUAL"


def test_quarterly_frequency_defaults_from_the_tab():
    gateway.write("financials_quarterly",
                  [{"symbol": "EEE", "fiscal_period": "FY2025Q1", "revenue": 100.0}],
                  source="upstox_fundamentals", actor="test")
    row = store.all_rows("financials_quarterly", entity="EEE")[0]
    assert row["statement_frequency"] == "QUARTERLY"


@pytest.mark.parametrize("label,expected", [
    ("Consolidated", "CONSOLIDATED"),
    ("CONSOLIDATED", "CONSOLIDATED"),
    ("consol", "CONSOLIDATED"),
    ("Standalone", "STANDALONE"),
    ("unconsolidated", "STANDALONE"),
    ("", "UNKNOWN"),
    (None, "UNKNOWN"),
    ("something else", "UNKNOWN"),
])
def test_vendor_type_labels_normalise(label, expected):
    assert statement_identity.normalise_statement_type(label) == expected


def test_an_unrecognised_type_is_unknown_rather_than_guessed():
    """Filing under the wrong type is worse than filing under none."""
    assert statement_identity.normalise_statement_type("cons0lidated") == "UNKNOWN"


# -- migration -------------------------------------------------------------


def _write_legacy(symbol: str, revenue: float) -> str:
    """A row as it looked before statement_type joined the key."""
    _write(symbol, statement_type="CONSOLIDATED", revenue=revenue)
    table = db.physical_table("financials_annual")
    db.execute(
        f"UPDATE {table} SET statement_type = NULL, statement_frequency = NULL"
        f" WHERE sys_entity = ?",
        (symbol.upper(),),
    )
    rows = db.query(f"SELECT row_id FROM {table} WHERE sys_entity = ?", (symbol.upper(),))
    return str(rows[0]["row_id"])


def test_untyped_rows_are_reported():
    _write_legacy("FFF", 1000.0)
    summary = statement_identity.unidentified_summary()
    assert summary["by_tab"]["financials_annual"]["unidentified"] == 1


def test_migration_dry_run_changes_nothing():
    _write_legacy("GGG", 1000.0)
    plan = statement_identity.backfill_identity(dry_run=True)
    assert plan["rows_typed"] == 1
    assert statement_identity.unidentified_summary()["unidentified_total"] == 1


def test_migration_types_and_rekeys_legacy_rows():
    old_id = _write_legacy("HHH", 1000.0)
    statement_identity.backfill_identity(dry_run=False)

    rows = store.all_rows("financials_annual", entity="HHH")
    assert len(rows) == 1
    assert rows[0]["statement_type"] == "UNKNOWN"
    # Re-keyed, so a later import of the same identity finds this row instead of
    # inserting a duplicate beside it.
    assert rows[0]["row_id"] != old_id


def test_a_reimport_after_migration_updates_rather_than_duplicates():
    _write_legacy("III", 1000.0)
    statement_identity.backfill_identity(dry_run=False)
    _write("III", revenue=1200.0)  # same UNKNOWN identity
    assert len(store.all_rows("financials_annual", entity="III")) == 1


def test_migration_is_idempotent():
    _write_legacy("JJJ", 1000.0)
    statement_identity.backfill_identity(dry_run=False)
    again = statement_identity.backfill_identity(dry_run=False)
    assert again["rows_typed"] == 0
    assert len(store.all_rows("financials_annual", entity="JJJ")) == 1
