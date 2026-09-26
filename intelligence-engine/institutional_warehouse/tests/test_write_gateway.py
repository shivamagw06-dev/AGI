"""The write gateway, and the architectural invariant that keeps it the only door."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

import pytest

os.environ.setdefault("INSTITUTIONAL_WAREHOUSE_ROOT", tempfile.mkdtemp(prefix="wh_gw_"))

from institutional_warehouse import (  # noqa: E402
    conflicts,
    db,
    gateway,
    missing_values,
    quality,
    store,
)

ENGINE_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def warehouse(tmp_path, monkeypatch):
    monkeypatch.setenv("INSTITUTIONAL_WAREHOUSE_ROOT", str(tmp_path))
    db.reset_backend()
    db.init(force=True)
    gateway.write(
        "company_master",
        [{"company_id": "AAA", "symbol": "AAA", "company_name": "Alpha Industries",
          "sector": "Industrials"}],
        source="yahoo_finance", actor="tester",
    )
    yield
    db.reset_backend()


# --------------------------------------------------------------------------
# The invariant
# --------------------------------------------------------------------------


def test_no_engine_calls_store_upsert_directly():
    """The rule that makes validation unavoidable, enforced rather than documented.

    A convention decays the first time someone is in a hurry. This test fails the
    build instead.
    """
    allowed = {
        ENGINE_ROOT / "institutional_warehouse" / "store.py",
        ENGINE_ROOT / "institutional_warehouse" / "gateway.py",
    }
    offenders: list[str] = []
    pattern = re.compile(r"\bstore\.upsert\s*\(")

    for path in ENGINE_ROOT.rglob("*.py"):
        if path in allowed or "/tests/" in str(path) or path.name.startswith("test_"):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        # Only warehouse writes matter; other packages have their own stores.
        if "institutional_warehouse" not in text:
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            if pattern.search(line) and "gateway" not in line:
                offenders.append(f"{path.relative_to(ENGINE_ROOT)}:{number}")

    assert not offenders, (
        "these write to the warehouse without passing the gateway: " + ", ".join(offenders)
    )


def test_every_collector_path_uses_the_gateway():
    for rel in ("institutional_warehouse/refresh.py",
                "institutional_warehouse/backfill/prices.py",
                "institutional_warehouse/backfill/statements.py",
                "institutional_warehouse/backfill/valuation_history.py",
                "institutional_warehouse/backfill/sources/nse_archive.py",
                "institutional_warehouse/formulas.py"):
        text = (ENGINE_ROOT / rel).read_text()
        assert "gateway.write(" in text, f"{rel} does not write through the gateway"


# --------------------------------------------------------------------------
# Missing value intelligence
# --------------------------------------------------------------------------


def test_zero_return_on_equity_is_missing_not_an_observation():
    """The live production bug: 'return on equity rose from 0 in FY19'."""
    verdict = missing_values.classify("roe", 0)
    assert verdict["status"] == missing_values.MISSING
    assert verdict["value"] is None
    assert missing_values.is_observation("roe", 0) is False


def test_zero_dividend_is_a_real_reading():
    verdict = missing_values.classify("dividend", 0)
    assert verdict["status"] == missing_values.OBSERVED
    assert verdict["value"] == 0.0


def test_a_loss_making_year_is_a_real_observation():
    assert missing_values.is_observation("pat", -500.0) is True
    assert missing_values.classify("pat", 0)["status"] == missing_values.OBSERVED


def test_blank_values_are_missing_not_zero():
    for blank in (None, "", "-", "NA", "n/a"):
        assert missing_values.classify("revenue", blank)["status"] == missing_values.MISSING


def test_the_gateway_strips_a_missing_zero_before_it_is_stored():
    gateway.write(
        "historical_ratios",
        [{"symbol": "AAA", "period": "FY19", "basis": "annual", "roe": 0, "net_margin": 12.0}],
        source="formula_engine", actor="tester",
    )
    row = store.fetch("historical_ratios", entity="AAA")["rows"][0]
    assert row["roe"] is None       # never narrated as "rose from zero"
    assert row["net_margin"] == 12.0


# --------------------------------------------------------------------------
# Validation on the collector path
# --------------------------------------------------------------------------


def test_an_invalid_collector_row_is_quarantined_not_stored():
    result = gateway.write(
        "daily_market_history",
        [{"symbol": "AAA", "date": "2026-07-31", "open": 10, "high": 5, "low": 8, "close": 9},
         {"symbol": "AAA", "date": "2026-07-30", "close": 100}],
        source="nse_bhavcopy", actor="tester",
    )
    assert result["written"] == 1
    assert result["quarantined"] == 1
    assert store.row_count("daily_market_history") == 1

    held = gateway.quarantined("daily_market_history")
    assert held["total"] == 1
    codes = {i["code"] for entry in held["entries"] for i in entry["issues"]}
    assert "impossible_range" in codes


def test_nothing_is_dropped_silently():
    """Quarantine exists so a stricter path cannot lose data that used to land."""
    gateway.write(
        "daily_market_history",
        [{"symbol": "", "date": "2026-07-31", "close": 10}],
        source="nse_bhavcopy", actor="tester",
    )
    held = gateway.quarantined()
    assert held["total"] == 1
    assert held["entries"][0]["source"] == "nse_bhavcopy"


# --------------------------------------------------------------------------
# Quality classification and confidence
# --------------------------------------------------------------------------


def test_every_written_row_carries_quality_and_confidence():
    gateway.write(
        "daily_market_history",
        [{"symbol": "AAA", "date": "2026-07-31", "open": 10, "high": 12, "low": 9,
          "close": 11, "volume": 1000}],
        source="nse_bhavcopy", actor="tester",
    )
    raw = db.query(
        f"SELECT sys_quality, sys_confidence, sys_confidence_score, sys_validation"
        f" FROM {db.physical_table('daily_market_history')}"
    )[0]
    assert raw["sys_quality"] == quality.OBSERVED
    assert raw["sys_confidence"] in ("high", "medium", "low")
    assert raw["sys_confidence_score"] > 0
    assert raw["sys_validation"] == "ok"


def test_source_decides_the_quality_class():
    assert quality.classify_source("yahoo_finance") == quality.VENDOR
    assert quality.classify_source("nse_bhavcopy") == quality.OBSERVED
    assert quality.classify_source("formula_engine") == quality.CALCULATED
    assert quality.classify_source("admin_override") == quality.OVERRIDE


def test_reasoning_skips_missing_and_conflicting_rows():
    assert quality.usable_for_reasoning(quality.OBSERVED, "high") is True
    assert quality.usable_for_reasoning(quality.MISSING, "high") is False
    assert quality.usable_for_reasoning(quality.CONFLICTING, "high") is False
    assert quality.usable_for_reasoning(quality.OBSERVED, "unknown") is False


def test_quality_summary_reports_the_distribution():
    gateway.write(
        "daily_market_history",
        [{"symbol": "AAA", "date": f"2026-07-{d:02d}", "close": 100 + d} for d in range(1, 6)],
        source="nse_bhavcopy", actor="tester",
    )
    summary = gateway.quality_summary()
    assert summary["rows_stamped"] >= 5
    assert summary["stamped_pct"] > 0


# --------------------------------------------------------------------------
# Cross-source conflicts
# --------------------------------------------------------------------------


def test_a_disagreement_between_sources_is_recorded_not_overwritten_silently():
    gateway.write(
        "financials_annual",
        [{"symbol": "AAA", "fiscal_year": "FY25", "revenue": 1000.0, "pat": 100.0}],
        source="capital_iq", actor="tester", reported_unit="inr_million",
    )
    # Both sides declare the same unit. Fundamentals rows now refuse an
    # overwrite from a source whose magnitude is unknown, so without this the
    # test would be measuring the unit guard instead of conflict detection.
    gateway.write(
        "financials_annual",
        [{"symbol": "AAA", "fiscal_year": "FY25", "revenue": 1400.0, "pat": 100.0}],
        source="yahoo_finance", actor="tester", reported_unit="inr_million",
    )
    report = conflicts.recent()
    assert report["total"] == 1
    entry = report["conflicts"][0]
    assert entry["field"] == "revenue"
    assert entry["held_source"] == "capital_iq"
    assert entry["incoming_source"] == "yahoo_finance"
    assert entry["gap_pct"] > 20
    # The incoming value still lands; the disagreement survives alongside it.
    assert store.fetch("financials_annual", entity="AAA")["rows"][0]["revenue"] == 1400.0


def test_rounding_differences_are_not_conflicts():
    gateway.write("financials_annual",
                  [{"symbol": "AAA", "fiscal_year": "FY25", "revenue": 1000.0}],
                  source="capital_iq", actor="tester")
    gateway.write("financials_annual",
                  [{"symbol": "AAA", "fiscal_year": "FY25", "revenue": 1000.5}],
                  source="yahoo_finance", actor="tester")
    assert conflicts.recent()["total"] == 0


def test_the_same_source_revising_itself_is_not_a_conflict():
    for revenue in (1000.0, 1500.0):
        gateway.write("financials_annual",
                      [{"symbol": "AAA", "fiscal_year": "FY25", "revenue": revenue}],
                      source="capital_iq", actor="tester")
    assert conflicts.recent()["total"] == 0


def test_the_formula_engine_is_not_treated_as_a_rival_source():
    gateway.write("historical_valuation",
                  [{"symbol": "AAA", "date": "2026-07-31", "pe": 20.0}],
                  source="yahoo_finance", actor="tester")
    gateway.write("historical_valuation",
                  [{"symbol": "AAA", "date": "2026-07-31", "pe": 35.0}],
                  source="formula_engine", actor="tester")
    assert conflicts.recent()["total"] == 0
