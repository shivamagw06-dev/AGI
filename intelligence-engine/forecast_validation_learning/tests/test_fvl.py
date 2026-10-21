"""Sprint 9.5 — Forecast Validation & Learning tests."""

from __future__ import annotations

import copy

from forecast_validation_learning.production import (
    calibration,
    dashboard,
    get_validation,
    health,
    history,
    learning,
    performance,
    register,
    validate,
    validate_entity,
)
from forecast_validation_learning.schema import NO_FVL_ACTIONS
from forecast_validation_learning.store import reset_all
from forecast_validation_learning import traces
from institutional_probability_confidence.production import assessment as ipci_assessment


def setup_function() -> None:
    reset_all()
    traces.clear()


def test_fvl_health() -> None:
    h = health()
    assert h["status"] == "ok"
    assert h["programme_short"] == "FVL"
    assert h["providers_queried_always"] == []
    assert "rewrite_historical_forecasts" in h["does_not"]
    assert h["phase9_layers"][-1] == "FVL"


def test_register_versions_before_publication() -> None:
    a = ipci_assessment("INFY")
    r1 = register(assessment=a)
    assert r1["published"] is True
    assert r1["version"] == 1
    assert r1["immutable"] is True
    assert r1["status"] == "Monitoring"
    assert r1["expected_outcome"]["modal_scenario"] in {"Bull", "Base", "Bear"}
    assert sum(r1["expected_outcome"]["probability_distribution"].values()) == 100

    a2 = ipci_assessment("INFY")
    r2 = register(assessment=a2)
    assert r2["version"] == 2
    assert r2["parent_forecast_id"] == r1["forecast_id"]
    assert r2["forecast_id"] != r1["forecast_id"]


def test_register_rejects_id_overwrite() -> None:
    from forecast_validation_learning.engine import ForecastValidationLearningEngine
    from forecast_validation_learning.schema import ExpectedOutcome, RegisteredForecast
    from forecast_validation_learning.store import REGISTRY

    eng = ForecastValidationLearningEngine()
    a = ipci_assessment("TCS")
    r = eng.register_assessment(a)
    fid = r["forecast_id"]
    dup = RegisteredForecast(
        forecast_id=fid,
        entity="TCS",
        expected_outcome=ExpectedOutcome(modal_scenario="Base"),
    )
    try:
        REGISTRY.register(dup)
        assert False, "should reject overwrite"
    except ValueError as exc:
        assert "immutable" in str(exc)


def test_validate_infosys_creates_immutable_records() -> None:
    out = validate_entity("INFY")
    assert out["providers_queried"] == [] if "providers_queried" in out else True
    assert out["history_rewritten"] is False
    assert out["forecast_snapshot_unchanged"] is True
    assert out["validation_status"] in {
        "Validated",
        "Partially Correct",
        "Incorrect",
        "Indeterminate",
    }
    assert out["expected_outcome"]["modal_scenario"]
    assert out["actual_outcome"]["realized_scenario"] in {"Bull", "Base", "Bear"}
    assert out["difference"]["summary"]
    assert out["score"]["overall"] >= 15
    assert out["learning"] is not None
    assert out["learning"]["history_rewritten"] is False
    assert out["learning"]["knowledge_factory_updated"] is False
    assert out["learning"]["topic"]
    assert out["learning"]["future_guidance"]

    # Snapshot immutable across validation
    fid = out["forecast_id"]
    before = copy.deepcopy(get_validation(fid)["forecast"]["assessment_snapshot"])
    validate(fid)  # second validation appends; still must not rewrite snapshot
    after = get_validation(fid)["forecast"]["assessment_snapshot"]
    assert before == after
    assert len(get_validation(fid)["validations"]) >= 2


def test_learning_without_history_rewrite() -> None:
    validate_entity("INFY")
    validate_entity("HDFCBANK")
    validate_entity("RELIANCE")
    pack = learning(limit=20)
    assert pack["n"] >= 3
    assert pack["history_rewritten"] is False
    for row in pack["learnings"]:
        assert row["history_rewritten"] is False
        assert row["category"]
        assert row["observation"]
        assert row["learning"]


def test_performance_and_bias() -> None:
    for t in ("INFY", "TCS", "HDFCBANK", "RELIANCE", "ITC"):
        validate_entity(t)
    perf = performance()
    assert perf["scores"]["n"] >= 5
    assert "overall" in perf["scores"]
    assert "company" in perf["by_scope"]
    assert perf["history_rewritten"] is False
    # Bias indicators may or may not fire depending on seeds — structure required
    assert "bias_indicators" in perf["bias"]
    assert perf["bias"]["model_retraining"] is False


def test_calibration_trends() -> None:
    for t in ("INFY", "HDFCBANK", "RELIANCE"):
        validate_entity(t)
    cal = calibration()
    assert cal["probability"]["n"] >= 3
    assert len(cal["probability"]["by_scenario"]) == 3
    assert cal["confidence"]["bands"]
    assert cal["probability"]["history_rewritten"] is False
    assert cal["confidence"]["history_rewritten"] is False
    assert cal["process_improvement_only"] is True


def test_history_api() -> None:
    validate_entity("INFY")
    h = history(entity="INFY", scope="company")
    assert h["n"] >= 1
    assert h["immutable_registry"] is True
    assert h["history_rewritten"] is False
    assert h["forecasts"][0]["snapshot_body_immutable"] is True


def test_sector_market_macro_validation() -> None:
    s = validate_entity("information_technology", scope="sector")
    assert s["scope"] == "sector"
    assert s["validation_status"] != "Pending"
    m = validate_entity("NIFTY", scope="market")
    assert m["scope"] == "market"
    mac = validate_entity("INDIA_MACRO", scope="macro")
    assert mac["scope"] == "macro"


def test_mission_control_and_traces() -> None:
    validate_entity("INFY")
    validate_entity("HDFCBANK")
    board = dashboard()
    assert board["board"] == "Forecast Validation & Learning"
    assert board["principles"]["history_never_rewritten"] is True
    assert board["active_forecasts"] >= 0
    assert board["validated_forecasts"] >= 2
    assert board["learning_generated"] >= 2
    assert board["forecast_score"]["n"] >= 2
    assert "probability_calibration" in board
    assert "confidence_calibration" in board
    assert board["phase9_complete"] is True
    for item in NO_FVL_ACTIONS:
        assert item in board["does_not"]
    names = {t["name"] for t in board["retrieval_performance"]["traces"]}
    assert "forecast_validation" in names
    assert "forecast_scoring" in names
    assert "forecast_learning" in names
    assert "forecast_calibration" in names


def test_no_trading_language() -> None:
    out = validate_entity("INFY")
    learning_blob = str(out.get("learning") or {}).lower()
    assert "target price" not in learning_blob
    assert " buy " not in f" {learning_blob} "
    assert " sell " not in f" {learning_blob} "
    assert out.get("is_recommendation") is not True
    assert "recommend_buy_sell" in health()["does_not"]
