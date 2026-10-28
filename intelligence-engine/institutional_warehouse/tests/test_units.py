"""Unit normalisation contract.

The scenario that motivates this module: Yahoo reports revenue in rupees and
Upstox reports the same revenue in crores. Without normalisation the two differ
by 10,000,000%, so every field on every row registers as a conflict and the
conflict log stops meaning anything.
"""

from __future__ import annotations

import os
import tempfile

import pytest

os.environ.setdefault("INSTITUTIONAL_WAREHOUSE_ROOT", tempfile.mkdtemp(prefix="wh_units_"))

from institutional_warehouse import db, gateway, schema, store, units  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_warehouse(tmp_path, monkeypatch):
    monkeypatch.setenv("INSTITUTIONAL_WAREHOUSE_ROOT", str(tmp_path))
    db.reset_backend()
    db.init(force=True)
    yield
    db.reset_backend()


# -- unit resolution -------------------------------------------------------


@pytest.mark.parametrize(
    "label,expected_scale",
    [
        ("crore", 10.0),
        ("CR", 10.0),
        ("In Crores", 10.0),
        ("lakh", 0.1),
        ("million", 1.0),
        ("INR Million", 1.0),
        ("billion", 1000.0),
        ("rupees", 1e-6),
    ],
)
def test_vendor_unit_labels_map_to_a_scale(label, expected_scale):
    name = units.canonical_unit_name(label)
    assert name is not None, label
    assert units.SCALE_TO_MILLION[name] == expected_scale


def test_unknown_unit_is_assumed_canonical_not_guessed():
    """Being flat is recoverable; guessing wrong by 10^7 is not."""
    unit, scale, method = units.resolve_unit(reported_unit="fathoms", source="nobody")
    assert scale == 1.0
    assert unit == units.CANONICAL_UNIT
    assert method == units.METHOD_ASSUMED


def test_declared_unit_beats_source_default():
    _, scale, method = units.resolve_unit(reported_unit="crore",
                                          source="yahoo_finance_statements")
    assert scale == 10.0
    assert method == units.METHOD_DECLARED


# -- what gets rescaled ----------------------------------------------------


def test_only_aggregate_money_is_rescaled():
    annual = schema.find_tab("financials_annual")
    rescaled = set(units.rescaled_columns(annual))
    assert {"revenue", "ebitda", "pat", "equity", "debt", "capex"} <= rescaled
    # Per-share and count columns must never be scaled to millions.
    assert "eps" not in rescaled
    assert "book_value" not in rescaled
    assert "shares_outstanding" not in rescaled


def test_prices_are_never_rescaled():
    prices = schema.find_tab("daily_market_history")
    rescaled = set(units.rescaled_columns(prices))
    assert rescaled == set(), "a closing price rescaled to millions is data loss"


def test_crore_payload_converts_to_inr_million():
    result = units.normalise_rows(
        "financials_annual",
        [{"symbol": "AAA", "fiscal_year": "FY2024", "revenue": 4580.0, "eps": 52.4,
          "shares_outstanding": 1_000_000}],
        source="upstox_fundamentals",
    )
    row = result["rows"][0]
    assert row["revenue"] == pytest.approx(45_800.0)   # 4,580 cr -> 45,800 mn
    assert row["eps"] == pytest.approx(52.4)           # untouched
    assert row["shares_outstanding"] == 1_000_000      # untouched
    assert row["sys_reported_unit"] == "crore"
    assert row["sys_unit_scale"] == 10.0


def test_rupee_payload_converts_to_inr_million():
    result = units.normalise_rows(
        "financials_annual",
        [{"symbol": "AAA", "fiscal_year": "FY2024", "revenue": 45_800_000_000.0}],
        source="yahoo_finance_statements",
    )
    assert result["rows"][0]["revenue"] == pytest.approx(45_800.0)


def test_row_level_units_in_overrides_the_source_default():
    result = units.normalise_rows(
        "financials_annual",
        [{"symbol": "AAA", "fiscal_year": "FY2024", "revenue": 45_800.0, "units_in": "million"}],
        source="upstox_fundamentals",
    )
    row = result["rows"][0]
    assert row["revenue"] == pytest.approx(45_800.0)
    assert row["sys_unit_scale"] == 1.0
    assert "units_in" not in row, "vendor unit hint must not leak into the tab"


# -- the false-conflict scenario ------------------------------------------


def test_same_fact_from_two_vendors_is_not_a_conflict():
    """Yahoo in rupees and Upstox in crores describe one revenue, not two."""
    gateway.write(
        "financials_annual",
        [{"symbol": "AAA", "fiscal_year": "FY2024", "revenue": 45_800_000_000.0}],
        source="yahoo_finance_statements",
        actor="test",
    )
    result = gateway.write(
        "financials_annual",
        [{"symbol": "AAA", "fiscal_year": "FY2024", "revenue": 4_580.0}],
        source="upstox_fundamentals",
        actor="test",
    )
    assert result["conflicts"] == 0, "unit mismatch must not read as disagreement"


def test_a_genuine_disagreement_is_still_recorded():
    gateway.write(
        "financials_annual",
        [{"symbol": "BBB", "fiscal_year": "FY2024", "revenue": 45_800_000_000.0}],
        source="yahoo_finance_statements",
        actor="test",
    )
    # 6,000 cr = 60,000 mn against Yahoo's 45,800 mn — a real gap.
    result = gateway.write(
        "financials_annual",
        [{"symbol": "BBB", "fiscal_year": "FY2024", "revenue": 6_000.0}],
        source="upstox_fundamentals",
        actor="test",
    )
    assert result["conflicts"] == 1


def test_gateway_reports_what_it_rescaled():
    result = gateway.write(
        "financials_annual",
        [{"symbol": "CCC", "fiscal_year": "FY2024", "revenue": 100.0, "ebitda": 20.0}],
        source="upstox_fundamentals",
        actor="test",
    )
    assert result["unit"] == "crore"
    assert result["values_rescaled"] == 2


# -- back-normalisation of legacy rows -------------------------------------


def _write_unstamped(symbol: str, revenue: float, source: str) -> None:
    """Simulate a row written before unit stamping existed."""
    gateway.write("financials_annual",
                  [{"symbol": symbol, "fiscal_year": "FY2023", "revenue": revenue}],
                  source=source, actor="test")
    table = db.physical_table("financials_annual")
    db.execute(
        f"UPDATE {table} SET revenue = ?, sys_reported_unit = NULL, sys_unit_scale = NULL,"
        f" sys_unit_method = NULL WHERE sys_entity = ?",
        (revenue, symbol.upper()),
    )


def test_unstamped_rows_are_reported_before_migration():
    _write_unstamped("DDD", 45_800_000_000.0, "yahoo_finance_statements")
    summary = units.unstamped_summary(["financials_annual"])
    assert summary["by_tab"]["financials_annual"]["unstamped"] == 1


def test_unstamped_money_is_not_compared_against_normalised_money():
    _write_unstamped("EEE", 45_800_000_000.0, "yahoo_finance_statements")
    result = gateway.write(
        "financials_annual",
        [{"symbol": "EEE", "fiscal_year": "FY2023", "revenue": 4_580.0}],
        source="upstox_fundamentals",
        actor="test",
    )
    assert result["conflicts"] == 0


def test_backfill_dry_run_changes_nothing():
    _write_unstamped("FFF", 45_800_000_000.0, "yahoo_finance_statements")
    plan = units.backfill_units(tab_ids=["financials_annual"], dry_run=True)
    assert plan["rows_stamped"] == 1
    row = store.all_rows("financials_annual", entity="FFF")[0]
    assert row["revenue"] == pytest.approx(45_800_000_000.0)


def test_backfill_converts_and_stamps_legacy_rows():
    _write_unstamped("GGG", 45_800_000_000.0, "yahoo_finance_statements")
    units.backfill_units(tab_ids=["financials_annual"], dry_run=False)
    row = store.all_rows("financials_annual", entity="GGG")[0]
    assert row["revenue"] == pytest.approx(45_800.0)
    assert units.unstamped_summary(["financials_annual"])["unstamped_total"] == 0


def test_backfill_is_idempotent():
    """Running twice must not scale a row twice."""
    _write_unstamped("HHH", 45_800_000_000.0, "yahoo_finance_statements")
    units.backfill_units(tab_ids=["financials_annual"], dry_run=False)
    units.backfill_units(tab_ids=["financials_annual"], dry_run=False)
    row = store.all_rows("financials_annual", entity="HHH")[0]
    assert row["revenue"] == pytest.approx(45_800.0)
