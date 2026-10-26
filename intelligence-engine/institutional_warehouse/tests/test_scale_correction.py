"""Rescaling a historical value is the most destructive thing here. Prove it holds."""

from __future__ import annotations

import os
import tempfile

import pytest

os.environ.setdefault("INSTITUTIONAL_WAREHOUSE_ROOT", tempfile.mkdtemp(prefix="sccor_"))

from institutional_warehouse import db  # noqa: E402
from institutional_warehouse import scale_correction as sc  # noqa: E402

TAB = "financials_annual"
REF = {"unit": "inr_million", "companies": 1, "unit_is_inferred": True, "data": {
    "ACME": {"FY2024": {"revenue": 5000.0, "ebitda": 1200.0, "pat": 800.0,
                        "assets": 9000.0, "equity": 4000.0, "cfo": 1100.0,
                        "debt": 2000.0, "cash": 700.0}}}}


@pytest.fixture(autouse=True)
def fresh(tmp_path, monkeypatch):
    monkeypatch.setenv("INSTITUTIONAL_WAREHOUSE_ROOT", str(tmp_path))
    db.reset_backend(); db.init(force=True)
    yield
    db.reset_backend()


def _rupee_row(**over):
    row = {"row_id": "r1", "symbol": "ACME", "fiscal_year": "FY2024",
           "source": "formula_engine",
           "revenue": 5000e6, "ebitda": 1200e6, "pat": 800e6, "assets": 9000e6,
           "equity": 4000e6, "cfo": 1100e6, "debt": 2000e6, "cash": 700e6}
    row.update(over)
    return row


def test_a_rupee_row_is_recognised_by_many_agreeing_fields():
    v = sc.assess_row(_rupee_row(), REF)
    assert v["correctable"] is True and v["factor"] == 1e6
    assert len(v["agreeing_fields"]) >= sc.MIN_AGREEING_FIELDS


def test_one_agreeing_field_is_not_enough():
    """One field matching a factor can be coincidence."""
    row = _rupee_row(ebitda=1200.0, pat=800.0, assets=9000.0, equity=4000.0,
                     cfo=1100.0, debt=2000.0, cash=700.0)
    v = sc.assess_row(row, REF)
    assert v["correctable"] is False
    assert "only_1_fields_agree" in v["reason"]


def test_a_row_whose_fields_disagree_is_left_alone():
    """Half in rupees, half in millions - a factor cannot be trusted."""
    row = _rupee_row(pat=800.0 * 1e7, assets=9000.0 * 1e7)
    v = sc.assess_row(row, REF)
    assert v["correctable"] is False
    assert v["reason"] == "fields_disagree_about_the_factor"


def test_a_correctly_scaled_row_is_never_touched():
    row = {"row_id": "ok", "symbol": "ACME", "fiscal_year": "FY2024",
           "revenue": 5000.0, "ebitda": 1200.0, "pat": 800.0, "assets": 9000.0}
    assert sc.assess_row(row, REF)["correctable"] is False


def test_no_reference_means_no_correction():
    v = sc.assess_row(_rupee_row(symbol="UNKNOWNCO"), REF)
    assert v["correctable"] is False
    assert v["reason"] == "no_reference_for_company_and_year"


def test_per_share_and_count_fields_are_never_rescaled():
    """shares_outstanding is derived as capital x 1e6 / face_value.

    Rescaling it is the 1,000,000x share-count error this exists to avoid.
    """
    from institutional_warehouse.value_plausibility import MONEY_FIELDS
    for field in ("eps", "book_value", "shares_outstanding"):
        assert field not in MONEY_FIELDS


def test_two_and_four_digit_fiscal_years_fold_together():
    for label in ("FY26", "FY2026", "2026"):
        assert sc.fiscal_key(label) == "FY2026"


def test_a_factor_of_ten_is_not_corrected_automatically():
    """A 10x gap can be a genuine restatement, not a scale error."""
    assert sc._nearest_factor(10.0) is None
    assert sc._nearest_factor(1e6) == 1e6


# --- the destructive path -------------------------------------------------

def _seed(row):
    cols = [k for k in row if k != "row_id"]
    db.execute(
        f"INSERT INTO {db.physical_table(TAB)} (row_id, sys_published, "
        + ", ".join(cols) + ") VALUES (?, 1, " + ",".join("?" for _ in cols) + ")",
        (row["row_id"], *[row[c] for c in cols]))


def test_apply_refuses_without_confirmation(monkeypatch):
    monkeypatch.setattr(sc, "load_reference", lambda: REF)
    _seed(_rupee_row())
    out = sc.apply(actor="t")
    assert out["ok"] is False and out["error"] == "confirm_required"
    stored = db.query(f"SELECT revenue FROM {db.physical_table(TAB)}")[0]["revenue"]
    assert stored == 5000e6, "a refused apply must change nothing"


def test_apply_rescales_and_rollback_restores_exactly(monkeypatch):
    monkeypatch.setattr(sc, "load_reference", lambda: REF)
    _seed(_rupee_row())
    before = dict(db.query(f"SELECT * FROM {db.physical_table(TAB)}")[0])

    out = sc.apply(actor="t", confirm=True)
    assert out["ok"] is True and out["rows_changed"] == 1
    after = db.query(f"SELECT revenue, pat FROM {db.physical_table(TAB)}")[0]
    assert after["revenue"] == pytest.approx(5000.0)
    assert after["pat"] == pytest.approx(800.0)

    back = sc.rollback(out["run_id"], actor="t", confirm=True)
    assert back["ok"] is True
    restored = db.query(f"SELECT * FROM {db.physical_table(TAB)}")[0]
    for field in ("revenue", "ebitda", "pat", "assets", "equity", "cfo", "debt", "cash"):
        assert restored[field] == pytest.approx(before[field]), field


def test_every_changed_value_is_backed_up_before_the_write(monkeypatch):
    monkeypatch.setattr(sc, "load_reference", lambda: REF)
    _seed(_rupee_row())
    out = sc.apply(actor="t", confirm=True)
    rows = db.query("SELECT * FROM wh_provenance_run_rows WHERE run_id = ?", (out["run_id"],))
    assert len(rows) == out["values_changed"]
    assert all(r["old_value"] for r in rows), "every prior value recorded"


def test_rollback_is_idempotent(monkeypatch):
    monkeypatch.setattr(sc, "load_reference", lambda: REF)
    _seed(_rupee_row())
    out = sc.apply(actor="t", confirm=True)
    sc.rollback(out["run_id"], actor="t", confirm=True)
    again = sc.rollback(out["run_id"], actor="t", confirm=True)
    assert again.get("already_rolled_back") is True


def test_rollback_refuses_without_confirmation(monkeypatch):
    monkeypatch.setattr(sc, "load_reference", lambda: REF)
    _seed(_rupee_row())
    out = sc.apply(actor="t", confirm=True)
    refused = sc.rollback(out["run_id"], actor="t")
    assert refused["ok"] is False and refused["error"] == "confirm_required"
    still = db.query(f"SELECT revenue FROM {db.physical_table(TAB)}")[0]["revenue"]
    assert still == pytest.approx(5000.0), "a refused rollback changes nothing"
