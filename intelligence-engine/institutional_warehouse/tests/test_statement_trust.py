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
    """Opt-in returns the fallback row only where it answers an open period.

    Both rows here are the same company-period, so the trusted one answers it
    and the fallback is suppressed rather than returned alongside.
    """
    rows = [row("upstox"), row("yahoo_finance_statements", "assumed_canonical",
                               fiscal_period="FY2026Q4")]
    assert len(st.select(QT, rows)) == 1
    out = st.select(QT, rows, include_unverified=True)
    assert len(out) == 2
    assert [r["trust"] for r in out] == [st.TRUSTED, st.FALLBACK]


def test_trusted_rows_come_first_when_fallback_is_included():
    """A caller taking the first row per period gets the declared one."""
    rows = [row("yahoo_finance_statements", "assumed_canonical",
                fiscal_period="FY2026Q4"), row("upstox")]
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


# --- 1. legacy write protection -------------------------------------------

def test_a_legacy_upstox_row_cannot_be_overwritten_by_an_undeclared_feed():
    """is_canonical is NULL on every quarterly row in production.

    The guard used to read that flag alone, so NULL was falsy and a feed with a
    known-but-undeclared unit overwrote a declared Upstox row with no refusal
    recorded. Read-time trust does not protect writes; the guard has to compute
    the same test.
    """
    from institutional_warehouse import canonical_rows

    prior = {"row_id": "r1", "symbol": "ACME", "source": "upstox",
             "is_canonical": None, "sys_unit_method": "declared",
             "sys_reported_unit": "crore", "revenue": 1000.0}
    incoming = {"row_id": "r1", "symbol": "ACME", "source": "yahoo_finance_statements",
                "is_canonical": False, "sys_unit_method": "source_default",
                "sys_reported_unit": "rupee", "revenue": 950.0}
    kept, counts = canonical_rows.guard(
        "financials_quarterly", [incoming], {"r1": prior}, key_of=lambda r: r["row_id"])
    assert kept == [] and counts.get("refused_downgrade") == 1


def test_upstox_still_replaces_a_legacy_fallback_row():
    from institutional_warehouse import canonical_rows

    prior = {"row_id": "r1", "source": "yahoo_finance_statements",
             "is_canonical": None, "sys_unit_method": "assumed_canonical"}
    incoming = {"row_id": "r1", "source": "upstox", "is_canonical": True,
                "sys_unit_method": "declared", "sys_reported_unit": "crore"}
    kept, _ = canonical_rows.guard(
        "financials_quarterly", [incoming], {"r1": prior}, key_of=lambda r: r["row_id"])
    assert len(kept) == 1, "an upgrade must still be allowed"


# --- 2. the read path actually uses it ------------------------------------

def test_the_canonical_series_prefers_a_declared_row_over_a_newer_one():
    """Quarterly selection fell through to last_updated, so the feed that wrote
    most recently won the period."""
    from institutional_warehouse.financials import canonical_statement_series

    rows = [{"source": "yahoo_finance_statements", "sys_unit_method": "assumed_canonical",
             "fiscal_period": "FY2027Q1", "statement_type": "CONSOLIDATED",
             "revenue": 9.9e9, "last_updated": "2026-08-22T12:00:00"},
            {"source": "upstox", "sys_unit_method": "declared",
             "fiscal_period": "FY2027Q1", "statement_type": "CONSOLIDATED",
             "revenue": 1000.0, "last_updated": "2026-08-01T00:00:00"}]
    out = canonical_statement_series(rows, period_key="fiscal_period", annual=False)
    assert out[0]["source"] == "upstox"


def test_annual_selection_is_unchanged_by_the_trust_rank():
    from institutional_warehouse.financials import canonical_statement_series

    rows = [{"source": "capital_iq_workbook", "statement_version": "capiq_workbook_2024",
             "sys_unit_method": "source_default", "fiscal_year": "FY2024",
             "statement_type": "CONSOLIDATED", "revenue": 5000.0},
            {"source": "yahoo_finance_statements", "sys_unit_method": "assumed_canonical",
             "fiscal_year": "FY2024", "statement_type": "CONSOLIDATED", "revenue": 4900.0}]
    out = canonical_statement_series(rows, period_key="fiscal_year", annual=True)
    assert out[0]["source"] == "capital_iq_workbook"


# --- 3. declared crore is converted before analytics ----------------------

def test_a_declared_crore_row_is_stored_in_inr_million():
    """3M India: 10,683 stored is Rs 1,068 crore, not Rs 10,683 crore."""
    from institutional_warehouse import units

    assert units.SCALE_TO_MILLION["crore"] == 10.0
    assert units.SOURCE_DEFAULT_UNIT.get("upstox") == "crore"


def test_trust_does_not_depend_on_the_reported_unit_being_million():
    """crore is a declared unit. Declared is the test, not which unit it is."""
    r = {"source": "upstox", "sys_unit_method": "declared", "sys_reported_unit": "crore"}
    assert st.is_trusted(QT, r) is True


# --- 4. labelling and duplicates ------------------------------------------

def test_every_returned_row_is_labelled_including_trusted_ones():
    rows = [row("upstox"), row("yahoo_finance_statements", "assumed_canonical",
                               fiscal_period="FY2026Q4")]
    out = st.select(QT, rows, include_unverified=True)
    assert all(r.get("trust") for r in out)
    assert {r["trust"] for r in out} == {st.TRUSTED, st.FALLBACK}


def test_a_fallback_row_is_not_returned_for_a_period_a_trusted_row_answers():
    """Two rows for one company-period is the silent duplicate this prevents."""
    rows = [row("upstox"),
            row("yahoo_finance_statements", "assumed_canonical", revenue=9.9e9)]
    out = st.select(QT, rows, include_unverified=True)
    assert len(out) == 1 and out[0]["source"] == "upstox"


def test_a_suppressed_fallback_row_is_still_inspectable():
    rows = [row("upstox"), row("yahoo_finance_statements", "assumed_canonical")]
    sup = st.suppressed(QT, rows)
    assert len(sup) == 1 and sup[0]["superseded_by_trusted"] is True


def test_fallback_still_fills_a_period_with_no_trusted_answer():
    rows = [row("upstox"),
            row("yahoo_finance_statements", "assumed_canonical",
                fiscal_period="FY2026Q4")]
    out = st.select(QT, rows, include_unverified=True)
    assert {r["fiscal_period"] for r in out} == {"FY2027Q1", "FY2026Q4"}


def test_coverage_reports_how_many_fallback_rows_are_superseded():
    rows = [row("upstox"), row("yahoo_finance_statements", "assumed_canonical")]
    assert st.coverage(QT, rows)["fallback_rows_superseded"] == 1


# --- the formula engine must not promote what it derives from -------------

def _seed_fallback_row(db, tab_id="financials_quarterly"):
    """An unverified row with unknown units, as production holds one.

    Seeded with the computed natural key. A hand-written row_id does not match
    what make_row_id derives, so the derivation writes a second row instead of
    updating this one and the test passes without exercising anything.
    """
    from institutional_warehouse import schema, store

    tab = schema.find_tab(tab_id)
    key = {"symbol": "ACME", "statement_type": "CONSOLIDATED",
           "fiscal_period": "FY2027Q1"}
    row_id = store.make_row_id(tab, key)
    db.execute(
        f"INSERT INTO {db.physical_table(tab_id)} (row_id, symbol, statement_type,"
        f" fiscal_period, source, cfo, capex, equity, shares_outstanding,"
        f" sys_published, sys_reported_unit, sys_unit_method, is_canonical)"
        f" VALUES (?,?,?,?,?,?,?,?,?,1,?,?,0)",
        (row_id, "ACME", "CONSOLIDATED", "FY2027Q1", "earnings_intelligence_p21",
         500.0, -100.0, 4000.0, 100.0, "inr_million", "assumed_canonical"))
    return row_id


def test_deriving_from_a_fallback_row_does_not_promote_it(tmp_path, monkeypatch):
    """The source-drift incident, as a regression test.

    formula_engine once rewrote `source` on rows it derived from - the journal
    recorded yahoo_finance_statements becoming formula_engine on a stable
    row_id. Deriving free_cash_flow from an unverified row must leave its
    source, unit metadata and trust exactly as they were: a derived column is
    not evidence that the row it came from is trustworthy.
    """
    monkeypatch.setenv("INSTITUTIONAL_WAREHOUSE_ROOT", str(tmp_path))
    from institutional_warehouse import db as _db
    _db.reset_backend(); _db.init(force=True)
    from institutional_warehouse import formulas

    row_id = _seed_fallback_row(_db)
    read = lambda: dict(_db.query(
        f"SELECT * FROM {_db.physical_table(QT)} WHERE row_id=?", (row_id,))[0])
    before = read()

    formulas.recalc_statement_derivations(actor="test")
    after = read()

    assert after["free_cash_flow"] == 400.0, "the derivation must actually land"
    for field in ("source", "sys_unit_method", "sys_reported_unit", "is_canonical"):
        assert after[field] == before[field], f"{field} was promoted"
    assert st.classify(QT, after) == st.FALLBACK
    _db.reset_backend()


def test_a_derived_row_stays_out_of_the_default_read(tmp_path, monkeypatch):
    """Deriving a column must not make the row readable as fact."""
    monkeypatch.setenv("INSTITUTIONAL_WAREHOUSE_ROOT", str(tmp_path))
    from institutional_warehouse import db as _db
    _db.reset_backend(); _db.init(force=True)
    from institutional_warehouse import formulas
    from institutional_warehouse.financials import canonical_statement_series

    _seed_fallback_row(_db)
    formulas.recalc_statement_derivations(actor="test")
    rows = _db.query(f"SELECT * FROM {_db.physical_table(QT)}")

    assert canonical_statement_series(
        [dict(r) for r in rows], period_key="fiscal_period", annual=False) == []
    opted_in = canonical_statement_series(
        [dict(r) for r in rows], period_key="fiscal_period", annual=False,
        include_unverified=True)
    assert len(opted_in) == 1 and opted_in[0]["trust"] == st.FALLBACK
    _db.reset_backend()


def test_a_derivation_should_be_allowed_onto_a_declared_row():
    """A derived-only write may land on a trusted row.

    It was refused because formula_engine has no declared unit, so its write
    counted as unknown-unit and the guard blocked it onto any row whose unit was
    known - so a trusted Upstox row could not receive free_cash_flow while a
    44%-suspect assumed_canonical row could.

    A derived-only payload asserts no unit. It carries computed columns onto a
    row that already has one, and derived_units records what each of those
    columns is in: free_cash_flow INR million, book_value INR per share, ratios
    nothing at all.
    """
    from institutional_warehouse import canonical_rows

    prior = {"row_id": "r1", "source": "upstox", "sys_unit_method": "declared",
             "sys_reported_unit": "crore", "is_canonical": 1}
    derived = {"row_id": "r1", "source": "upstox", "free_cash_flow": 400.0}
    kept, _counts = canonical_rows.guard(
        QT, [derived], {"r1": prior}, key_of=lambda r: r["row_id"],
        source="formula_engine")
    assert len(kept) == 1, "a derivation should be able to land on a trusted row"
