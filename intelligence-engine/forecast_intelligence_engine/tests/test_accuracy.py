from forecast_intelligence_engine.accuracy import evaluation_rows, evaluate_predictions, prediction_rows, target_period


def _pack():
    lines = {
        "revenue": {"NQ": 102.0, "FY+1": 110.0, "FY+2": 121.0, "FY+3": 133.1, "FY+5": 161.05},
        "pat": {"FY+1": 22.0},
    }
    scenario = {
        "base_period": "FY25",
        "base_values": {"revenue": 100.0, "pat": 20.0},
        "lines": lines,
    }
    return {
        "symbol": "TEST",
        "generated_at": "2026-08-13T10:00:00+00:00",
        "version": "8.5",
        "probabilities": {"bull": 20, "base": 60, "bear": 20},
        "forecast_quality": {"forecast_confidence": "High", "score": 0.8},
        "modules": {"scenarios": {"scenarios": {"base": scenario}}},
    }


def test_target_period_preserves_fiscal_year_style():
    assert target_period("FY25", "FY+1") == "FY26"
    assert target_period("FY2025", "FY+3") == "FY2028"
    assert target_period("2025-03-31", "FY+1") == "2026-03-31"
    assert target_period("2024-25", "FY+2") == "2026-27"


def test_predictions_are_immutable_metric_vintages_and_skip_nq():
    rows = prediction_rows(_pack())
    assert len(rows) == 5
    assert {r["target_period"] for r in rows} == {"FY26", "FY27", "FY28", "FY30"}
    assert all(r["generated_at"] == "2026-08-13T10:00:00+00:00" for r in rows)
    assert all(r["horizon"] != "NQ" for r in rows)


def test_evaluator_waits_for_exact_future_actual_and_scores_bias():
    rows = prediction_rows(_pack())
    actuals = [
        {"fiscal_year": "FY25", "revenue": 100, "pat": 20},
        {"fiscal_year": "FY26", "revenue": 105, "pat": 18},
    ]
    scored = evaluate_predictions(rows, actuals, evaluated_at="2027-06-01T00:00:00+00:00")
    assert len(scored) == 2
    revenue = next(r for r in scored if r["metric"] == "revenue")
    assert revenue["actual_period"] == "FY26"
    assert revenue["error_pct"] == -4.5455
    assert revenue["ape_pct"] == 4.5455
    assert revenue["direction_correct"] is True
    assert revenue["accuracy_band"] == "EXCELLENT"
    pat = next(r for r in scored if r["metric"] == "pat")
    assert pat["direction_correct"] is False
    assert pat["calibration_status"] == "ALIGNED"


def test_no_matching_actual_means_no_accuracy_row():
    rows = prediction_rows(_pack())
    assert evaluate_predictions(rows, [{"fiscal_year": "FY25", "revenue": 100}]) == []


def test_evaluation_registry_exposes_missing_and_revised_actuals():
    rows = prediction_rows(_pack())
    missing = evaluation_rows(rows, [{"fiscal_year": "FY25", "revenue": 100}])
    assert {r["outcome_status"] for r in missing} == {"MISSING_ACTUAL"}
    revised = evaluation_rows(rows, [{"fiscal_year": "FY26", "revenue": 105, "pat": 18, "restated": True}])
    fy1 = [r for r in revised if r["target_period"] == "FY26"]
    assert {r["outcome_status"] for r in fy1} == {"DATA_REVISION"}
    assert all(r["requires_review"] is True for r in fy1)


def test_evaluation_registry_marks_exact_outcomes_valid():
    rows = prediction_rows(_pack())
    outcomes = evaluation_rows(rows, [{"fiscal_year": "FY26", "revenue": 105, "pat": 18}], sector="IT")
    fy1 = [r for r in outcomes if r["target_period"] == "FY26"]
    assert {r["outcome_status"] for r in fy1} == {"VALID"}
    assert all(r["sector"] == "IT" for r in fy1)
