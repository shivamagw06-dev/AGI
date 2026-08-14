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


def test_empty_calibration_fails_closed():
    result = calibration_summary([], [])
    assert result["valid_accuracy_outcomes"] == 0
    assert result["status"] == "ACCUMULATING_OUTCOMES"
    assert all(passed is False for passed in result["gates"].values())
