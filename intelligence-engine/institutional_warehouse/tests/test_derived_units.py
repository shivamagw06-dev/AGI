"""Each derived field has its own unit, and deriving promotes nothing."""

from __future__ import annotations

import pytest

from institutional_warehouse import derived_units as du

KEYS = {"symbol": "ACME", "statement_type": "CONSOLIDATED",
        "fiscal_period": "FY2027Q1", "source": "upstox"}


def test_the_three_derived_units_are_distinct():
    """One blanket unit for formula_engine would state book_value is in
    INR million, and it is not."""
    assert du.unit_of("free_cash_flow") == du.INR_MILLION
    assert du.unit_of("book_value") == du.INR_PER_SHARE
    assert du.unit_of("roe") is du.UNITLESS
    assert du.unit_of("gross_margin") is du.UNITLESS


def test_a_reported_field_is_not_a_derived_field():
    for field in ("revenue", "pat", "assets", "cfo", "capex"):
        assert du.is_derived_field(field) is False


def test_a_derived_only_payload_is_recognised():
    assert du.is_derived_only({**KEYS, "free_cash_flow": 400.0, "book_value": 40.0})


def test_a_payload_carrying_a_reported_value_is_not_derived_only():
    """A reported write wearing a derived write's clothes is not exempt."""
    assert du.is_derived_only({**KEYS, "free_cash_flow": 400.0,
                               "revenue": 9.9e9}) is False


def test_system_columns_do_not_make_a_payload_look_reported():
    """The gateway attaches these before the guard sees the row.

    Ignoring only the natural key made a derived payload look like reported
    data, and it was refused.
    """
    row = {**KEYS, "free_cash_flow": 400.0, "sys_reported_unit": "crore",
           "sys_unit_method": "declared", "sys_unit_scale": 10.0,
           "is_canonical": 1, "canonical_blockers": None, "period_key": "FY2027Q1"}
    assert du.is_derived_only(row) is True


def test_an_empty_payload_is_not_derived_only():
    assert du.is_derived_only(dict(KEYS)) is False


def test_only_aggregate_money_counts_as_carrying_money():
    assert du.carries_money({**KEYS, "free_cash_flow": 400.0}) is True
    assert du.carries_money({**KEYS, "book_value": 40.0}) is False
    assert du.carries_money({**KEYS, "roe": 12.5}) is False
    assert du.carries_money({**KEYS, "revenue": 1000.0}) is True


def test_a_batch_splits_into_derived_and_reported():
    derived, reported = du.split([
        {**KEYS, "free_cash_flow": 1.0},
        {**KEYS, "revenue": 2.0},
    ])
    assert len(derived) == 1 and len(reported) == 1


# --- the guard --------------------------------------------------------------

def test_a_derivation_lands_on_a_declared_row():
    from institutional_warehouse import canonical_rows

    prior = {"row_id": "r1", "source": "upstox", "sys_unit_method": "declared",
             "sys_reported_unit": "crore", "is_canonical": 1}
    derived = {"row_id": "r1", **KEYS, "free_cash_flow": 400.0}
    kept, _ = canonical_rows.guard("financials_quarterly", [derived],
                                   {"r1": prior}, key_of=lambda r: r["row_id"])
    assert len(kept) == 1


def test_a_reported_write_is_still_refused_onto_a_declared_row():
    """The exemption is for derived columns, not a way around the guard."""
    from institutional_warehouse import canonical_rows

    prior = {"row_id": "r1", "source": "upstox", "sys_unit_method": "declared",
             "sys_reported_unit": "crore", "is_canonical": 1}
    reported = {"row_id": "r1", "source": "yahoo_finance_statements",
                "sys_unit_method": "assumed_canonical", "revenue": 9.9e9}
    kept, counts = canonical_rows.guard("financials_quarterly", [reported],
                                        {"r1": prior}, key_of=lambda r: r["row_id"])
    assert kept == [] and counts.get("refused_downgrade") == 1


# --- end to end -------------------------------------------------------------

@pytest.mark.parametrize("source,expect_trust", [
    ("upstox", "trusted"),
    ("yahoo_finance_statements", "unverified_fallback"),
])
def test_deriving_preserves_provenance_and_trust(source, expect_trust, tmp_path,
                                                 monkeypatch):
    """Neither direction may move: a trusted row stays trusted, an unverified
    row is not promoted by receiving a derived column."""
    monkeypatch.setenv("INSTITUTIONAL_WAREHOUSE_ROOT", str(tmp_path))
    from institutional_warehouse import db, formulas, gateway
    from institutional_warehouse import statement_trust as st
    db.reset_backend(); db.init(force=True)
    tab = "financials_quarterly"

    gateway.write(tab, [{"symbol": "ACME", "statement_type": "CONSOLIDATED",
                         "fiscal_period": "FY2027Q1", "source": source,
                         "cfo": 500.0, "capex": -100.0, "equity": 4000.0,
                         "shares_outstanding": 100.0}], source=source, actor="seed")
    read = lambda: dict(db.query(f"SELECT * FROM {db.physical_table(tab)}")[0])
    before = read()
    formulas.recalc_statement_derivations(actor="test")
    after = read()

    assert after["free_cash_flow"] is not None, "the derivation must land"
    for field in ("source", "sys_reported_unit", "sys_unit_method",
                  "sys_unit_scale", "is_canonical"):
        assert after[field] == before[field], f"{field} changed"
    assert st.classify(tab, after) == expect_trust
    db.reset_backend()
