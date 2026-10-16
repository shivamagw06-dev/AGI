from forecast_intelligence_engine.accuracy import calibration_summary


def test_calibration_requires_real_outcomes_and_consensus():
    rows = [
        {"ape_pct": 10, "direction_correct": True, "calibration_status": "ALIGNED"},
        {"ape_pct": 30, "direction_correct": False, "calibration_status": "OVERCONFIDENT"},
    ]
    evaluations = [{"outcome_status": "VALID", "sector": "Banks"} for _ in rows]
    result = calibration_summary(rows, evaluations, minimum_outcomes=2, minimum_sector_outcomes=2)
    assert result["median_ape_pct"] == 20.0
    assert result["directional_accuracy_pct"] == 50.0
    assert result["gates"]["consensus_vintages_available"] is False
    assert result["status"] == "ACCUMULATING_OUTCOMES"
    assert result["execution_eligible"] is False


def test_calibration_accepts_real_consensus_metric_coverage():
    rows = [{"ape_pct": 10, "direction_correct": True, "calibration_status": "ALIGNED"}] * 2
    evaluations = [{"outcome_status": "VALID", "sector": "Banks"}] * 2
    result = calibration_summary(
        rows,
        evaluations,
        minimum_outcomes=2,
        minimum_sector_outcomes=2,
        consensus_vintage_count=100,
        consensus_symbol_count=20,
        consensus_matched_predictions=20,
        consensus_match_coverage_pct=100,
    )
    assert result["gates"]["consensus_vintages_available"] is True
    assert result["status"] == "RESEARCH_CALIBRATED"


def test_empty_calibration_fails_closed():
    result = calibration_summary([], [], prediction_count=0)
    assert result["valid_accuracy_outcomes"] == 0
    assert result["status"] == "ACCUMULATING_OUTCOMES"
    assert all(passed is False for passed in result["gates"].values())
    assert result["outcome_diagnostic"] == "NO_PREDICTIONS"


def test_open_forecasts_are_explained_without_becoming_accuracy():
    evaluations = [
        {"outcome_status": "MISSING_ACTUAL", "requires_review": False},
        {"outcome_status": "PERIOD_MISMATCH", "requires_review": True},
    ]
    result = calibration_summary([], evaluations, prediction_count=12)
    assert result["forecast_predictions"] == 12
    assert result["outcome_status_counts"] == {"MISSING_ACTUAL": 1, "PERIOD_MISMATCH": 1}
    assert result["review_required"] == 1
    assert result["outcome_diagnostic"] == "NO_MATURED_VALID_OUTCOMES"
    assert result["execution_eligible"] is False
