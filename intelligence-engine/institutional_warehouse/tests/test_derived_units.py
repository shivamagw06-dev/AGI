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
                                   {"r1": prior}, key_of=lambda r: r["row_id"],
                                   source="formula_engine")
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


# --- the exemption requires the authorised writer, not just the shape -------

PRIOR = {"row_id": "r1", "source": "upstox", "sys_unit_method": "declared",
         "sys_reported_unit": "crore", "is_canonical": 1}


def _guard(row, source):
    from institutional_warehouse import canonical_rows
    return canonical_rows.guard("financials_quarterly", [row], {"r1": PRIOR},
                                key_of=lambda r: r["row_id"], source=source)


def test_the_formula_engine_may_write_derived_columns():
    kept, _ = _guard({"row_id": "r1", "symbol": "ACME", "free_cash_flow": 400.0},
                     "formula_engine")
    assert len(kept) == 1


@pytest.mark.parametrize("source", [
    "yahoo_finance_statements", "financial_connector",
    "earnings_intelligence_p21", "upstox",
])
def test_another_feed_cannot_use_the_exemption_by_shaping_its_payload(source):
    """Shape is not entitlement.

    Keying the exemption on payload shape alone let any feed reach a trusted row
    its reported writes are refused from, simply by sending a row containing
    nothing but free_cash_flow.
    """
    kept, counts = _guard(
        {"row_id": "r1", "symbol": "ACME", "free_cash_flow": 9.9e9}, source)
    assert kept == [] and counts


def test_the_formula_engine_carrying_a_reported_field_is_refused():
    """A reported write from the formula engine is still a reported write."""
    kept, counts = _guard(
        {"row_id": "r1", "symbol": "ACME", "free_cash_flow": 400.0,
         "revenue": 9.9e9}, "formula_engine")
    assert kept == [] and counts.get("refused_downgrade") == 1


def test_both_halves_are_required():
    from institutional_warehouse import derived_units as d
    derived = {"symbol": "ACME", "free_cash_flow": 400.0}
    reported = {"symbol": "ACME", "revenue": 1.0}
    assert d.is_derived_write(derived, "formula_engine") is True
    assert d.is_derived_write(derived, "yahoo_finance_statements") is False
    assert d.is_derived_write(reported, "formula_engine") is False


# --- provenance and keys cannot be changed through the exemption -----------

def test_a_derived_write_may_not_re_own_the_row():
    """The drift incident arriving by a new door.

    A derived payload claiming a different source rewrote provenance through
    the exemption - upstox became formula_engine on a stable row_id. Refused
    rather than stripped, because a caller sending the wrong source is a bug
    worth surfacing.
    """
    kept, counts = _guard(
        {"row_id": "r1", "symbol": "ACME", "source": "formula_engine",
         "free_cash_flow": 400.0}, "formula_engine")
    assert kept == [] and counts.get("refused_provenance_change") == 1


def test_a_derived_write_preserving_the_parent_source_is_allowed():
    """What the real formula engine sends: the parent's own source."""
    kept, _ = _guard({"row_id": "r1", "symbol": "ACME", "source": "upstox",
                      "free_cash_flow": 400.0}, "formula_engine")
    assert len(kept) == 1


def test_provenance_survives_a_real_derivation(tmp_path, monkeypatch):
    monkeypatch.setenv("INSTITUTIONAL_WAREHOUSE_ROOT", str(tmp_path))
    from institutional_warehouse import db, formulas, gateway, schema, store
    db.reset_backend(); db.init(force=True)
    tab_id = "financials_quarterly"
    key = {"symbol": "ACME", "statement_type": "CONSOLIDATED",
           "fiscal_period": "FY2027Q1"}
    gateway.write(tab_id, [{**key, "source": "upstox", "cfo": 500.0,
                            "capex": -100.0, "equity": 4000.0,
                            "shares_outstanding": 100.0}],
                  source="upstox", actor="seed")
    row_id = store.make_row_id(schema.find_tab(tab_id), key)
    read = lambda: dict(db.query(
        f"SELECT * FROM {db.physical_table(tab_id)} WHERE row_id=?", (row_id,))[0])
    before = read()
    formulas.recalc_statement_derivations(actor="test")
    after = read()
    assert after["free_cash_flow"] is not None
    for field in ("source", "symbol", "statement_type", "fiscal_period",
                  "sys_reported_unit", "sys_unit_method", "is_canonical"):
        assert after[field] == before[field], f"{field} changed"
    db.reset_backend()


def test_a_derived_write_without_a_parent_row_is_refused():
    """Update-only. Without a parent there is nothing to add a column to.

    Inserting would create a row holding free_cash_flow and nothing else - no
    revenue, no units, no reported source - which then reads as a fallback row
    for a period nobody reported.
    """
    from institutional_warehouse import canonical_rows

    kept, counts = canonical_rows.guard(
        "financials_quarterly",
        [{"row_id": "missing", "symbol": "ORPHANCO", "free_cash_flow": 123.0}],
        {}, key_of=lambda r: r["row_id"], source="formula_engine")
    assert kept == [] and counts.get("refused_derived_without_parent") == 1


def test_a_reported_write_may_still_create_a_row():
    """The update-only rule is for derived columns, not for real data."""
    from institutional_warehouse import canonical_rows

    kept, _ = canonical_rows.guard(
        "financials_quarterly",
        [{"row_id": "new", "symbol": "NEWCO", "revenue": 1000.0}],
        {}, key_of=lambda r: r["row_id"], source="upstox")
    assert len(kept) == 1


def test_a_derived_write_cannot_increase_the_row_count(tmp_path, monkeypatch):
    monkeypatch.setenv("INSTITUTIONAL_WAREHOUSE_ROOT", str(tmp_path))
    from institutional_warehouse import db, gateway
    db.reset_backend(); db.init(force=True)
    tab_id = "financials_quarterly"
    gateway.write(tab_id, [{"symbol": "ACME", "statement_type": "CONSOLIDATED",
                            "fiscal_period": "FY2027Q1", "source": "upstox",
                            "cfo": 500.0}], source="upstox", actor="seed")
    count = lambda: db.query(
        f"SELECT COUNT(*) AS n FROM {db.physical_table(tab_id)}")[0]["n"]
    before = count()
    for payload in (
        {"symbol": "ORPHANCO", "statement_type": "CONSOLIDATED",
         "fiscal_period": "FY2027Q1", "free_cash_flow": 123.0},
        {"symbol": "ACME", "statement_type": "CONSOLIDATED",
         "fiscal_period": "FY2099Q4", "free_cash_flow": 456.0},
        {"symbol": "ACME", "statement_type": "STANDALONE",
         "fiscal_period": "FY2027Q1", "free_cash_flow": 789.0},
    ):
        gateway.write(tab_id, [{**payload, "source": "formula_engine"}],
                      source="formula_engine", actor="t")
    assert count() == before, "a derived write must never add a row"
    db.reset_backend()


def test_a_derived_write_cannot_target_another_company(tmp_path, monkeypatch):
    """Two real rows. A derivation for one must not alter the other."""
    monkeypatch.setenv("INSTITUTIONAL_WAREHOUSE_ROOT", str(tmp_path))
    from institutional_warehouse import db, gateway
    db.reset_backend(); db.init(force=True)
    tab_id = "financials_quarterly"
    for symbol, cfo in (("ACME", 500.0), ("OTHERCO", 900.0)):
        gateway.write(tab_id, [{"symbol": symbol, "statement_type": "CONSOLIDATED",
                                "fiscal_period": "FY2027Q1", "source": "upstox",
                                "cfo": cfo, "capex": -100.0}],
                      source="upstox", actor="seed")
    gateway.write(tab_id, [{"symbol": "ACME", "statement_type": "CONSOLIDATED",
                            "fiscal_period": "FY2027Q1", "source": "upstox",
                            "free_cash_flow": 400.0}],
                  source="formula_engine", actor="t")
    other = db.query(f"SELECT * FROM {db.physical_table(tab_id)}"
                     f" WHERE symbol='OTHERCO'")[0]
    assert other["free_cash_flow"] is None, "the other company must be untouched"
    assert other["source"] == "upstox"
    db.reset_backend()
