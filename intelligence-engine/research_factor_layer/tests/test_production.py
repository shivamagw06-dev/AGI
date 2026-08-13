from research_factor_layer.production import _eligible, _ev_reconciliation, _is_financial, _multiple_valid, _quality_results


def test_point_in_time_eligibility_uses_filing_date():
    assert _eligible({"filing_date": "2024-05-20"}, "2024-06-01") == (True, True)
    assert _eligible({"filing_date": "2024-07-20"}, "2024-06-01") == (False, True)
    assert _eligible({}, "2024-06-01") == (True, False)


def test_bank_multiple_eligibility_blocks_ev_ebitda():
    bank = {"sector": "Financial Services", "industry": "Private Bank"}
    assert _is_financial(bank)
    assert _multiple_valid("ev_ebitda", 8, {}, bank) == (False, "company_type_incompatible")
    assert _multiple_valid("pb", 2, {}, bank) == (True, "pass")


def test_invalid_denominators_are_explicit():
    industrial = {"sector": "Industrials"}
    assert _multiple_valid("pe", -4, {}, industrial) == (False, "negative_or_missing_denominator")
    assert _multiple_valid("pe", 300, {}, industrial) == (False, "near_zero_earnings_denominator")
    assert _multiple_valid("ev_ebitda", 120, {}, industrial) == (False, "near_zero_ebitda_denominator")


def test_enterprise_value_reconciliation_is_a_visible_gate():
    assert _ev_reconciliation({}) == (None, None)
    matches, difference = _ev_reconciliation({"enterprise_value": 115, "market_cap": 100, "debt": 20, "cash": 5})
    assert matches is True
    assert difference == 0
    matches, difference = _ev_reconciliation({"enterprise_value": 200, "market_cap": 100, "debt": 20, "cash": 5})
    assert matches is False
    assert round(difference, 3) == 0.425


def test_five_accounting_factors_share_versioned_pit_limited_contract():
    rows = []
    for year in range(2017, 2027):
        rows.append({"symbol": "AAA", "fiscal_year": f"FY{year}", "statement_type": "UNKNOWN",
                     "revenue": 100 + year - 2017, "ebitda": 25, "ebit": 20, "pbt": 18, "pat": 14,
                     "equity": 60, "debt": 20, "cash": 10, "cfo": 18, "capex": -5,
                     "free_cash_flow": 13, "depreciation": 5, "research_and_development": 0,
                     "finance_cost": -2, "accounts_receivable": 12, "inventory": 8, "assets": 100,
                     "total_liabilities": 40, "goodwill": 0, "acquisition_spending": 0,
                     "dividends_paid": -3, "buybacks": 0, "debt_issuance": 0, "debt_repayment": -1})
    result = _quality_results("2026-12-31", ["AAA"], {"AAA": rows})["AAA"]
    for name in ("quality_compounder", "earnings_quality", "sustainable_growth", "capital_allocation", "balance_sheet_risk"):
        assert name in result
        assert result[name]["methodology_status"] == "IN_DEVELOPMENT"
        assert result[name]["validation_status"] == "POINT_IN_TIME_LIMITED"
        assert result[name]["score"] is not None
