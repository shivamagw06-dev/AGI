"""Core warehouse behaviour: schema, storage, overrides, versions, audit."""

from __future__ import annotations

import os
import tempfile

import pytest

os.environ.setdefault("INSTITUTIONAL_WAREHOUSE_ROOT", tempfile.mkdtemp(prefix="wh_core_"))

from institutional_warehouse import audit, db, importer, production, store, validation, versions  # noqa: E402
from institutional_warehouse.schema import TABS, tab  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_warehouse(tmp_path, monkeypatch):
    monkeypatch.setenv("INSTITUTIONAL_WAREHOUSE_ROOT", str(tmp_path))
    db.reset_backend()
    db.init(force=True)
    yield
    db.reset_backend()


# --------------------------------------------------------------------------
# Schema
# --------------------------------------------------------------------------


def test_workbook_has_required_core_tabs():
    ids = [t.id for t in TABS]
    for expected in (
        "company_master",
        "daily_market_history",
        "financials_annual",
        "financials_quarterly",
        "historical_ratios",
        "annual_sector_ratios",
        "historical_valuation",
        "consensus",
        "research_intelligence",
        "research_timeline",
        "corporate_actions",
        "ownership",
        "hedge_fund_factors",
        "company_intelligence",
        "data_quality",
    ):
        assert expected in ids


def test_computed_tabs_are_read_only():
    assert tab("historical_ratios").read_only
    assert tab("hedge_fund_factors").read_only
    assert not tab("company_master").read_only
    assert tab("daily_market_history").append_only


def test_every_tab_creates_a_physical_table():
    info = db.info()
    for t in TABS:
        assert t.id in info["row_counts"]


# --------------------------------------------------------------------------
# Storage
# --------------------------------------------------------------------------


def _seed_master(symbol: str = "AXISBANK") -> None:
    store.upsert(
        "company_master",
        [{"company_id": symbol, "symbol": symbol, "company_name": "Axis Bank Limited",
          "sector": "Financials", "industry": "Banks", "active": True}],
        source="test",
        actor="tester",
    )


def test_upsert_inserts_then_detects_no_change():
    _seed_master()
    first = store.fetch("company_master")
    assert first["total"] == 1
    assert first["rows"][0]["company_name"] == "Axis Bank Limited"

    again = store.upsert(
        "company_master",
        [{"company_id": "AXISBANK", "symbol": "AXISBANK", "company_name": "Axis Bank Limited"}],
        source="test",
        actor="tester",
    )
    assert again["unchanged"] == 1
    assert again["updated"] == 0


def test_upsert_updates_bump_version_and_journal():
    _seed_master()
    store.upsert(
        "company_master",
        [{"company_id": "AXISBANK", "symbol": "AXISBANK", "company_name": "Axis Bank Ltd"}],
        source="test",
        actor="tester",
    )
    row = store.fetch("company_master")["rows"][0]
    assert row["company_name"] == "Axis Bank Ltd"
    assert row["_meta"]["version"] == 2
    history = versions.cell_history("company_master", row["row_id"])
    assert any(h["column"] == "company_name" for h in history)


def test_all_rows_paginates_past_max_limit(monkeypatch):
    """Coverage audits request limit>MAX_LIMIT; must not silently stop at one page."""
    monkeypatch.setattr(store, "MAX_LIMIT", 10)
    _seed_master("AAA")
    market = [
        {"symbol": "AAA", "date": f"2026-01-{(i):02d}", "close": float(i)}
        for i in range(1, 26)
    ]
    store.upsert("daily_market_history", market, source="test", actor="tester")
    total = store.fetch("daily_market_history", limit=1)["total"]
    assert total == 25
    page = store.fetch("daily_market_history", limit=100)
    assert page["returned"] == 10  # per-request clamp
    all_of_them = store.all_rows("daily_market_history", limit=100)
    assert len(all_of_them) == 25


def test_append_tab_keeps_each_period_as_its_own_row():
    rows = [
        {"symbol": "AXISBANK", "date": "2026-07-30", "close": 1000.0},
        {"symbol": "AXISBANK", "date": "2026-07-31", "close": 1010.0},
    ]
    store.upsert("daily_market_history", rows, source="nse", actor="tester")
    page = store.fetch("daily_market_history")
    assert page["total"] == 2
    dates = sorted(r["date"] for r in page["rows"])
    assert dates == ["2026-07-30", "2026-07-31"]


def test_row_id_is_deterministic():
    t = tab("daily_market_history")
    a = store.make_row_id(t, {"symbol": "axisbank", "date": "2026-07-31"})
    b = store.make_row_id(t, {"symbol": "AXISBANK", "date": "2026-07-31"})
    assert a == b
    assert store.make_row_id(t, {"symbol": "", "date": "2026-07-31"}) is None


# --------------------------------------------------------------------------
# Override layer
# --------------------------------------------------------------------------


def test_edit_creates_override_without_destroying_imported_value():
    _seed_master()
    row_id = store.fetch("company_master")["rows"][0]["row_id"]
    result = store.set_cells(
        "company_master",
        [{"row_id": row_id, "column": "sector", "value": "Banking"}],
        actor="founder",
        reason="reclassified",
    )
    assert result["applied"] == 1

    effective = store.get("company_master", row_id)
    assert effective["sector"] == "Banking"
    assert "sector" in effective["_meta"]["overridden"]

    base = store.raw_row("company_master", row_id)
    assert base["sector"] == "Financials"  # imported value untouched


def test_clearing_an_override_falls_back_to_the_imported_value():
    _seed_master()
    row_id = store.fetch("company_master")["rows"][0]["row_id"]
    store.set_cells("company_master", [{"row_id": row_id, "column": "sector", "value": "Banking"}],
                    actor="founder")
    store.clear_override("company_master", row_id, "sector", actor="founder")
    assert store.get("company_master", row_id)["sector"] == "Financials"


def test_computed_columns_reject_manual_edits():
    store.upsert(
        "historical_ratios",
        [{"symbol": "AXISBANK", "period": "FY2026", "basis": "annual", "roe": 12.0}],
        source="formula_engine",
        actor="system",
    )
    row_id = store.fetch("historical_ratios")["rows"][0]["row_id"]
    result = store.set_cells("historical_ratios", [{"row_id": row_id, "column": "roe", "value": 99}],
                             actor="founder")
    assert result["ok"] is False
    assert "read_only" in result["error"]


def test_edit_on_a_computed_column_of_an_editable_tab_is_rejected():
    store.upsert("daily_market_history",
                 [{"symbol": "AXISBANK", "date": "2026-07-31", "close": 1000.0}],
                 source="nse", actor="tester")
    row_id = store.fetch("daily_market_history")["rows"][0]["row_id"]
    result = store.set_cells("daily_market_history",
                             [{"row_id": row_id, "column": "market_cap", "value": 123}],
                             actor="founder")
    assert result["applied"] == 0
    assert result["rejected"][0]["error"] == "column_not_editable"


# --------------------------------------------------------------------------
# Versions
# --------------------------------------------------------------------------


def test_version_history_diff_and_restore():
    _seed_master()
    row_id = store.fetch("company_master")["rows"][0]["row_id"]
    store.set_cells("company_master", [{"row_id": row_id, "column": "sector", "value": "Banking"}],
                    actor="founder", reason="v2")
    store.set_cells("company_master", [{"row_id": row_id, "column": "sector", "value": "Private Banks"}],
                    actor="founder", reason="v3")

    hist = production.history("company_master", row_id)
    assert hist["ok"] is True
    assert len(hist["cells"]) >= 2
    assert hist["latest_version"] >= 2

    target = min(int(v["version"]) for v in hist["versions"])
    restored = production.restore("company_master", row_id, version=target, actor="founder")
    assert restored["ok"] is True
    assert store.get("company_master", row_id)["sector"] in ("Banking", "Financials")


# --------------------------------------------------------------------------
# Audit
# --------------------------------------------------------------------------


def test_every_action_is_audited():
    _seed_master()
    row_id = store.fetch("company_master")["rows"][0]["row_id"]
    store.set_cells("company_master", [{"row_id": row_id, "column": "city", "value": "Mumbai"}],
                    actor="founder", reason="profile")
    log = audit.recent(limit=20)
    actions = {entry["action"] for entry in log["entries"]}
    assert "edit" in actions or "bulk_edit" in actions
    assert all(entry["actor"] for entry in log["entries"])


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------


def test_validation_rejects_impossible_and_duplicate_rows():
    _seed_master()
    report = validation.validate_payload(
        "daily_market_history",
        [
            {"symbol": "AXISBANK", "date": "2026-07-31", "open": 10, "high": 5, "low": 8, "close": 9},
            {"symbol": "AXISBANK", "date": "2026-07-30", "close": 100},
            {"symbol": "AXISBANK", "date": "2026-07-30", "close": 101},
            {"symbol": "", "date": "2026-07-29", "close": 5},
        ],
    )
    assert report["rejected_count"] == 3
    assert report["accepted_count"] == 1
    codes = {issue["code"] for entry in report["rejected"] for issue in entry["issues"]}
    assert "impossible_range" in codes
    assert "duplicate_key" in codes
    assert "missing_key" in codes


def test_validation_flags_unknown_company_reference():
    report = validation.validate_payload("consensus", [
        {"symbol": "NOTREAL", "consensus_date": "2026-07-31", "target_price": 100},
    ])
    _seed_master()
    report2 = validation.validate_payload("consensus", [
        {"symbol": "NOTREAL", "consensus_date": "2026-07-31", "target_price": 100},
    ])
    assert report["ok"] is True  # no master yet -> nothing to reference
    codes = {i["code"] for w in report2["warnings"] for i in w["issues"]}
    assert "broken_reference" in codes


def test_ownership_beyond_the_float_is_impossible():
    _seed_master()
    report = validation.validate_payload("ownership", [
        {"symbol": "AXISBANK", "as_of": "2026-06-30", "promoter_holding": 70, "public_holding": 45},
    ])
    assert report["rejected_count"] == 1
    assert report["rejected"][0]["issues"][0]["code"] == "impossible_ownership"


def test_institutional_holding_inside_the_public_float_is_valid():
    """Institutional holding is a slice of the public float, not an addition to it."""
    _seed_master()
    report = validation.validate_payload("ownership", [
        {"symbol": "AXISBANK", "as_of": "2026-06-30", "promoter_holding": 70,
         "institutional_holding": 21, "fii": 12, "dii": 9, "public_holding": 30},
    ])
    assert report["rejected_count"] == 0
    assert report["accepted_count"] == 1


def test_institutional_holding_above_the_float_warns():
    _seed_master()
    report = validation.validate_payload("ownership", [
        {"symbol": "AXISBANK", "as_of": "2026-06-30", "promoter_holding": 70,
         "institutional_holding": 45, "public_holding": 30},
    ])
    assert report["rejected_count"] == 0
    codes = {i["code"] for w in report["warnings"] for i in w["issues"]}
    assert "ownership_mismatch" in codes


# --------------------------------------------------------------------------
# Import
# --------------------------------------------------------------------------


def test_excel_paste_maps_columns_and_commits():
    _seed_master()
    pasted = "Symbol\tDate\tClose\tVolume\nAXISBANK\t31-Jul-2026\t1,010.50\t1250000\n"
    staged = importer.stage("daily_market_history", text=pasted, actor="founder")
    assert staged["ok"] is True
    assert staged["accepted"] == 1
    assert staged["mapping"]["mapping"]["Close"] == "close"

    committed = importer.commit(staged["import_id"], actor="founder", recalculate=False)
    assert committed["inserted"] == 1
    row = store.fetch("daily_market_history")["rows"][0]
    assert row["close"] == 1010.5
    assert row["date"] == "2026-07-31"
    assert row["volume"] == 1250000


def test_import_rejects_invalid_rows_before_commit():
    _seed_master()
    staged = importer.stage(
        "daily_market_history",
        rows=[{"symbol": "AXISBANK", "date": "2026-07-31", "high": 1, "low": 5, "close": 3}],
        actor="founder",
    )
    assert staged["accepted"] == 0
    assert staged["rejected"] == 1
    committed = importer.commit(staged["import_id"], actor="founder")
    assert committed["ok"] is False
    assert store.row_count("daily_market_history") == 0


def test_capital_iq_style_headers_are_auto_mapped():
    t = tab("financials_annual")
    mapping = importer.map_headers(t, ["Ticker", "FY", "Total Revenue", "Net Income", "Total Debt"])
    assert mapping["mapping"]["Ticker"] == "symbol"
    assert mapping["mapping"]["FY"] == "fiscal_year"
    assert mapping["mapping"]["Total Revenue"] == "revenue"
    assert mapping["mapping"]["Net Income"] == "pat"
    assert mapping["mapping"]["Total Debt"] == "debt"


def test_export_round_trips_through_csv():
    _seed_master()
    result = production.export("company_master")
    assert result["ok"] is True
    assert "Company Name" in result["csv"].splitlines()[0]
    assert "AXISBANK" in result["csv"]
