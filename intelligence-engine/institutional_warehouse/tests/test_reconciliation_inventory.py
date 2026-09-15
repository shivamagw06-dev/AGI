"""The dry run, tested on the exact shape of the live defect.

RELIANCE's June 2026 quarter, as actually stored: four rows, four labels, three
sources, three magnitudes. The inventory has to group them as one period, pick
the row the contract would read, and - the part that decides whether anything is
safe to retire - say which losing rows hold a metric the winner does not.
"""

from __future__ import annotations

import os
import tempfile

import pytest

os.environ.setdefault("INSTITUTIONAL_WAREHOUSE_ROOT", tempfile.mkdtemp(prefix="wh_inv_"))

from institutional_warehouse import db, reconciliation_inventory as inv, store  # noqa: E402

TAB = "financials_quarterly"


@pytest.fixture(autouse=True)
def fresh(tmp_path, monkeypatch):
    monkeypatch.setenv("INSTITUTIONAL_WAREHOUSE_ROOT", str(tmp_path))
    db.reset_backend()
    db.init(force=True)
    yield
    db.reset_backend()


def _seed(rows):
    """Write rows straight to the table, bypassing the gateway.

    Deliberate: these are legacy rows written before the rules existed, and the
    gateway would now normalise them into exactly the shape the inventory is
    supposed to find broken.
    """
    for i, row in enumerate(rows):
        payload = dict(row)
        payload.setdefault("symbol", "RELIANCE")
        db.execute(
            f"INSERT INTO {db.physical_table(TAB)} "
            f"(row_id, symbol, statement_type, fiscal_period, period_key, revenue, pat,"
            f" assets, source, sys_published, sys_reported_unit, sys_unit_method)"
            f" VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)",
            (f"row{i}", payload["symbol"], payload.get("statement_type"),
             payload.get("fiscal_period"), payload.get("period_key"),
             payload.get("revenue"), payload.get("pat"), payload.get("assets"),
             payload.get("source"), payload.get("unit"), payload.get("method")))


#: The live rows, as they actually sit in the warehouse today.
LIVE_SHAPE = [
    {"source": "upstox", "fiscal_period": "FY2027Q1", "statement_type": "CONSOLIDATED",
     "revenue": 3160180.0, "unit": "crore", "method": "declared"},
    {"source": "yahoo_finance_statements", "fiscal_period": "FY27Q1",
     "statement_type": "UNKNOWN", "revenue": 3094680.0, "assets": 21781400.0,
     "unit": "rupee", "method": "source_default"},
    {"source": "financial_connector", "fiscal_period": "Q1 FY27",
     "statement_type": "UNKNOWN", "revenue": 1660130000000.0,
     "unit": None, "method": None},
    {"source": "financial_connector", "fiscal_period": "Q1 FY27",
     "statement_type": None, "revenue": 1660130000000.0,
     "unit": None, "method": None},
]


def test_four_spellings_of_one_quarter_are_one_group():
    _seed(LIVE_SHAPE)
    report = inv.inventory(TAB)
    assert report["totals"]["rows"] == 4
    keys = {g["period_key"] for g in report["sample_groups"]}
    assert keys == {"2026-07-01"}, "one quarter, however it was spelled"


def test_the_whole_quarter_is_one_group_whatever_the_statement_types():
    """Grouping by statement type is what made this report dangerous.

    An untyped row in its own group looks like the only holder of everything it
    contains, even when the typed row beside it covers the same quarter.
    """
    _seed(LIVE_SHAPE)
    report = inv.inventory(TAB)
    assert len(report["sample_groups"]) == 1
    assert report["sample_groups"][0]["rows"] == 4


def test_the_same_source_writing_one_period_twice_is_counted():
    _seed(LIVE_SHAPE)
    report = inv.inventory(TAB)
    assert report["totals"]["same_source_duplicate_rows"] == 1


def test_upstox_wins_a_quarter_and_the_untrusted_rows_do_not():
    _seed(LIVE_SHAPE)
    report = inv.inventory(TAB)
    group = report["sample_groups"][0]
    assert list(group["winners"]) == ["CONSOLIDATED"]
    assert group["winners"]["CONSOLIDATED"]["source"] == "upstox"
    assert {r["source"] for r in group["losers"]} == {
        "yahoo_finance_statements", "financial_connector"}


def test_a_row_holding_a_metric_the_winner_lacks_is_not_retirable():
    """The check that stops the obvious answer from deleting data.

    Yahoo is not trusted for revenue and is still the only row carrying assets.
    """
    _seed(LIVE_SHAPE)
    report = inv.inventory(TAB)
    group = report["sample_groups"][0]
    yahoo = next(r for r in group["losers"] if r["source"] == "yahoo_finance_statements")
    assert "assets" in yahoo["metrics_only_here"]
    assert report["totals"]["rows_sole_holder_of_a_metric"] >= 1


def test_rows_of_unknown_magnitude_are_counted_and_never_compared():
    """Comparing rupees against INR million reports every field as a conflict."""
    _seed(LIVE_SHAPE)
    report = inv.inventory(TAB)
    assert report["totals"]["rows_with_unknown_units"] == 2
    group = report["sample_groups"][0]
    connector = next(r for r in group["losers"] if r["source"] == "financial_connector")
    assert connector["unit_known"] is False
    assert connector["conflicts_with_winner"] == [], "not comparable, so not compared"


def test_a_group_with_nothing_trustworthy_is_reported_not_guessed():
    _seed([r for r in LIVE_SHAPE if r["source"] != "upstox"])
    report = inv.inventory(TAB)
    assert report["totals"]["groups_with_no_canonical_candidate"] >= 1
    assert all(g["winner_reason"] == inv.NO_CANDIDATE
               for g in report["sample_groups"] if not g["winners"])


def test_the_inventory_writes_nothing():
    """It exists to be read before anything is retired."""
    _seed(LIVE_SHAPE)
    before = [dict(r) for r in store.all_rows(TAB)]
    report = inv.inventory(TAB)
    assert report["dry_run"] is True
    assert [dict(r) for r in store.all_rows(TAB)] == before


def test_consolidated_and_standalone_both_survive_the_same_quarter():
    """Two real facts, not two opinions. Neither may be retired as a duplicate."""
    _seed([
        {"source": "upstox", "fiscal_period": "FY2027Q1", "statement_type": "CONSOLIDATED",
         "revenue": 3160180.0, "unit": "crore", "method": "declared"},
        {"source": "upstox", "fiscal_period": "FY2027Q1", "statement_type": "STANDALONE",
         "revenue": 1660130.0, "unit": "crore", "method": "declared"},
    ])
    report = inv.inventory(TAB)
    group = report["sample_groups"][0]
    assert set(group["winners"]) == {"CONSOLIDATED", "STANDALONE"}
    assert group["losers"] == []
    assert report["totals"]["rows_that_survive"] == 2
    assert report["totals"]["rows_retirable"] == 0


def test_a_metric_on_the_standalone_row_is_not_called_sole_holder_of_the_group():
    """Coverage is measured against everything that survives, not one winner."""
    _seed([
        {"source": "upstox", "fiscal_period": "FY2027Q1", "statement_type": "CONSOLIDATED",
         "revenue": 3160180.0, "unit": "crore", "method": "declared"},
        {"source": "upstox", "fiscal_period": "FY2027Q1", "statement_type": "STANDALONE",
         "revenue": 1660130.0, "assets": 21781400.0, "unit": "crore", "method": "declared"},
        {"source": "yahoo_finance_statements", "fiscal_period": "FY27Q1",
         "statement_type": "UNKNOWN", "assets": 21781400.0,
         "unit": "rupee", "method": "source_default"},
    ])
    report = inv.inventory(TAB)
    yahoo = next(r for r in report["sample_groups"][0]["losers"]
                 if r["source"] == "yahoo_finance_statements")
    assert yahoo["metrics_only_here"] == [], "assets is on the standalone winner"
    assert report["totals"]["rows_retirable"] == 1


def test_the_counts_the_review_actually_needs():
    """Every number reported before anything is retired, on the live shape."""
    _seed(LIVE_SHAPE)
    t = inv.inventory(TAB)["totals"]
    assert t["rows"] == 4
    assert t["groups"] == 1
    assert t["duplicate_groups"] == 1
    assert t["raw_label_duplicate_groups"] == 1, "FY2027Q1, FY27Q1 and Q1 FY27"
    assert t["same_source_duplicate_rows"] == 1, "financial_connector wrote it twice"
    assert t["cross_source_duplicate_rows"] == 3, "three rows are not the winner's source"
    assert t["unknown_or_null_statement_type_rows"] == 3
    assert t["rows_with_unknown_units"] == 2
    assert t["rows_that_survive"] == 1
    assert t["manual_review_rows"] >= 1


def test_manual_review_covers_everything_that_is_neither_kept_nor_droppable():
    """A row is only retirable when a survivor already holds all of it."""
    _seed(LIVE_SHAPE)
    t = inv.inventory(TAB)["totals"]
    losers = t["rows"] - t["rows_that_survive"]
    assert t["rows_retirable"] + t["rows_sole_holder_of_a_metric"] == losers
    assert t["manual_review_rows"] == t["rows_sole_holder_of_a_metric"]


def test_rows_are_counted_by_unit_classification():
    _seed(LIVE_SHAPE)
    by_unit = inv.inventory(TAB)["by_unit"]
    assert by_unit["unstamped"] == 2, "the two rows nobody declared a magnitude for"
    assert by_unit["crore"] == 1
    assert by_unit["rupee"] == 1


def test_compare_reads_each_row_once_for_both_halves(monkeypatch):
    """The before/after must describe the same rows.

    Two separate inventory runs against a live warehouse do not: schedulers
    write these tabs every few minutes. This asserts the row query happens once
    per company, not once per half.
    """
    from institutional_warehouse import db as _db

    _seed(LIVE_SHAPE)
    real = _db.query
    row_reads = []

    def counting_query(sql, params=()):
        if "WHERE sys_published = 1 AND symbol = ?" in sql:
            row_reads.append(params)
        return real(sql, params)

    monkeypatch.setattr(_db, "query", counting_query)
    out = inv.compare(TAB)

    assert out["ok"] is True and out["before_after_row_consistent"] is True
    assert out["comparison_basis"] == "same_rows_per_symbol"
    assert out["whole_table_snapshot"] is False
    assert len(row_reads) == len(set(row_reads)), "each company must be read exactly once"


def test_compare_before_matches_a_plain_inventory():
    """The 'before' half must equal what the inventory reports on its own."""
    _seed(LIVE_SHAPE)
    plain = inv.inventory(TAB)["totals"]
    both = inv.compare(TAB)

    for key in ("rows", "rows_that_survive", "rows_with_unknown_units",
                "manual_review_rows", "groups_with_no_canonical_candidate"):
        assert both["before"][key] == plain[key], f"{key} drifted between the two paths"


#: A Capital IQ row in the state the production tab is actually in: labelled
#: inr_million, with nobody having established that. Without one of these the
#: simulation has nothing to change and a delta test passes vacuously.
CAPIQ_ASSUMED_ROW = {
    "source": "capital_iq_workbook", "fiscal_period": "FY27Q1",
    "statement_type": "CONSOLIDATED", "revenue": 3100000.0,
    "unit": "inr_million", "method": "assumed_canonical",
}


def test_compare_delta_matches_the_simulated_inventory():
    _seed(LIVE_SHAPE + [CAPIQ_ASSUMED_ROW])
    simulated = inv.inventory(TAB, simulate_unit_provenance=True)["totals"]
    both = inv.compare(TAB)

    for key in ("rows_that_survive", "rows_with_unknown_units"):
        assert both["after"][key] == simulated[key]
        assert both["delta"][key] == simulated[key] - both["before"][key]

    # The comparison has to be measuring something, or it proves nothing.
    assert both["delta"]["rows_with_unknown_units"] != 0
    assert both["before"] != both["after"]
