from research_factor_layer.production import _eligible, _ev_reconciliation, _is_financial, _multiple_valid


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
