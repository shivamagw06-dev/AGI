from institutional_warehouse.financials import canonical_statement_series


def test_annual_series_prefers_capiq_within_same_year():
    rows = [
        {"fiscal_year": "FY2024", "statement_type": "CONSOLIDATED", "source": "upstox", "sys_unit_method": "declared", "pat": 10},
        {"fiscal_year": "FY2024", "statement_type": "CONSOLIDATED", "statement_version": "capiq_workbook_2024", "source": "capital_iq_workbook", "sys_unit_method": "declared", "pat": 12},
        {"fiscal_year": "FY2025", "statement_type": "CONSOLIDATED", "source": "upstox", "sys_unit_method": "declared", "pat": 15},
    ]
    selected = canonical_statement_series(rows, period_key="fiscal_year", annual=True)
    assert [row["pat"] for row in selected] == [12, 15]


def test_quarterly_series_does_not_apply_capiq_priority():
    rows = [
        {"fiscal_period": "FY2025Q1", "statement_type": "CONSOLIDATED", "source": "upstox", "sys_unit_method": "declared", "pat": 10},
        {"fiscal_period": "FY2025Q1", "statement_type": "CONSOLIDATED", "statement_version": "capiq_workbook_2025", "source": "capital_iq_workbook", "sys_unit_method": "declared", "pat": 12},
    ]
    selected = canonical_statement_series(rows, period_key="fiscal_period", annual=False)
    assert selected[0]["pat"] == 10


def test_an_undeclared_row_is_not_returned_by_default():
    """The filtering the ranking alone did not do.

    Ranking picks the best row for a period and then returns it whatever its
    trust, so a period no declared feed covers still handed an unverified row to
    every caller. On the quarterly tab that was 6,616 of 7,355 selections.
    """
    rows = [{"fiscal_period": "FY2025Q1", "statement_type": "CONSOLIDATED",
             "source": "yahoo_finance_statements",
             "sys_unit_method": "assumed_canonical", "pat": 99}]
    assert canonical_statement_series(rows, period_key="fiscal_period",
                                      annual=False) == []


def test_an_undeclared_row_is_returned_when_asked_for_explicitly():
    rows = [{"fiscal_period": "FY2025Q1", "statement_type": "CONSOLIDATED",
             "source": "yahoo_finance_statements",
             "sys_unit_method": "assumed_canonical", "pat": 99}]
    out = canonical_statement_series(rows, period_key="fiscal_period", annual=False,
                                     include_unverified=True)
    assert len(out) == 1 and out[0]["trust"] == "unverified_fallback"


def test_every_returned_row_carries_a_trust_label():
    rows = [{"fiscal_year": "FY2024", "statement_type": "CONSOLIDATED",
             "source": "capital_iq_workbook", "sys_unit_method": "declared", "pat": 12}]
    out = canonical_statement_series(rows, period_key="fiscal_year", annual=True)
    assert out[0]["trust"] == "trusted"
