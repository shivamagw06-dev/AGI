from research_factor_layer.math import (
    effective_tax_rate,
    free_cash_flow,
    invested_capital,
    nopat,
    percentile_rank,
    reinvestment_rate,
    weighted_score,
    z_score,
)


def test_nopat_and_effective_tax_rate():
    tax = effective_tax_rate(100, 75)
    assert tax == 0.25
    assert nopat(120, tax) == 90


def test_invested_capital_financing_definition():
    assert invested_capital(500, 200, 50) == 650
    assert invested_capital(None, 200, 50) is None
    assert invested_capital(10, 0, 20) is None


def test_free_cash_flow_treats_capex_as_cash_outflow_for_either_sign():
    assert free_cash_flow(100, 25) == 75
    assert free_cash_flow(100, -25) == 75


def test_reinvestment_requires_every_input_instead_of_fabricating_zero():
    assert reinvestment_rate(20, 10, 5, 100) == 0.25
    assert reinvestment_rate(20, None, 5, 100) is None


def test_percentile_and_z_score():
    values = [1, 2, 3, 4, 5]
    assert percentile_rank(values, 2) == 40
    assert round(z_score(values, 3), 8) == 0


def test_weighted_score_renormalizes_only_available_components():
    assert round(weighted_score({"a": 80, "b": None, "c": 40}, {"a": 0.5, "b": 0.3, "c": 0.2}, minimum=2), 3) == 68.571
    assert weighted_score({"a": 80, "b": None}, {"a": 1, "b": 1}, minimum=2) is None
