from valuation_intelligence.conditioning import (
    percentile_rank, premium_discount, quality_matrix, reconcile_sources,
)
from valuation_intelligence.history import historical_windows_from_series


def test_historical_windows_are_3_5_10_year_distributions():
    windows = historical_windows_from_series(list(range(10, 20)), 18, source="test")
    assert windows["3y"].observations == 3
    assert windows["5y"].observations == 5
    assert windows["10y"].observations == 10
    assert windows["10y"].percentile == 90.0


def test_peer_percentile_and_premium_discount():
    assert percentile_rank(25, [18, 22, 24, 28]) == 75.0
    assert premium_discount(25, 22) == 13.6


def test_quality_premium_is_conditioned_on_fundamentals():
    result = quality_matrix(
        historical_percentile=82, peer_premium_pct=14,
        roe=24, peer_roe=18, eps_cagr=16, peer_eps_cagr=11,
    )
    assert result["label"] == "QUALITY_PREMIUM"


def test_reconciliation_blocks_material_conflict():
    accepted = reconcile_sources({"workbook": 24.8, "capiq": 25.1, "afe": 25.0})
    conflict = reconcile_sources({"workbook": 24.8, "capiq": 31.4, "afe": 25.0})
    assert accepted["status"] == "ACCEPTED"
    assert conflict["status"] == "VALUATION_DATA_CONFLICT"
