from forecast_intelligence_engine import runtime
from institutional_warehouse import store


def test_forecast_outcome_tabs_are_symbol_addressable():
    for tab_id in ("forecast_metric_predictions", "forecast_evaluations", "forecast_accuracy"):
        assert store.get_tab(tab_id).entity_column == "symbol"


def test_vintage_repair_rebuilds_one_missing_summary(monkeypatch):
    predicted = {"DONE"}

    def all_rows(tab, *, entity=None, limit=5000):
        if tab == "forecast_company":
            return [{"symbol": "DONE"}, {"symbol": "MISSING"}]
        if tab == "forecast_metric_predictions" and entity:
            return [{"symbol": entity}] if entity in predicted else []
        return []

    def build(symbol):
        predicted.add(symbol)
        return {"ok": True, "status": "PASS", "symbol": symbol}

    monkeypatch.setattr(store, "all_rows", all_rows)
    monkeypatch.setattr(store, "entities", lambda tab: sorted(predicted))
    monkeypatch.setattr(runtime, "build_forecast", build)
    runtime._STATE["vintage_cursor"] = 0

    result = runtime.repair_prediction_vintages(batch=1)
    assert result["missing_before"] == 1
    assert result["attempted"] == 1
    assert result["repaired"] == 1
    assert result["errors"] == 0


def test_web_process_cannot_run_worker_batch(monkeypatch):
    monkeypatch.setenv("AGI_ROLE", "web")
    result = runtime.process_batch(batch=1)
    assert result["ok"] is False
    assert result["attempted"] == 0
    assert result["reason"] == "forecast_runtime_owned_by_gather_worker"


def test_runtime_snapshot_exposes_compact_last_batch_state():
    runtime._STATE["last_batch"] = {"attempted": 1, "completed": 1, "failed": 0}
    snapshot = runtime.runtime_snapshot()
    assert snapshot["last_batch"]["completed"] == 1
    assert "started_mono" not in snapshot


def test_data_readiness_skip_is_not_classified_as_engine_failure(monkeypatch):
    writes = []
    monkeypatch.setenv("AGI_ROLE", "gather_worker")
    monkeypatch.setattr(runtime, "_paged", lambda tab, max_rows=0: (
        [{"symbol": "TEST", "queue_status": "PENDING"}] if tab == "forecast_runtime" else []
    ))
    monkeypatch.setattr(runtime, "_upsert_runtime", lambda symbol, **fields: writes.append((symbol, fields)))
    monkeypatch.setattr(runtime, "build_forecast", lambda symbol: {
        "ok": False,
        "status": "FAIL",
        "dqiv": {"errors": ["data_readiness:quarterly_history_below_8_periods"]},
    })
    monkeypatch.setattr(runtime, "repair_prediction_vintages", lambda batch=1: {"repaired": 0})
    monkeypatch.setattr(runtime, "sweep_outcomes", lambda batch=1: {"accuracy_rows_written": 0, "errors": 0})
    monkeypatch.setattr(runtime, "sweep_strategy_validation", lambda: {"ok": True, "attempted": 0})
    runtime._STATE["last_strategy_validation_mono"] = 0

    result = runtime.process_batch(batch=1)

    terminal = writes[-1][1]
    assert terminal["queue_status"] == "SKIPPED"
    assert terminal["lifecycle"] == "WAITING_STATEMENTS"
    assert result["failed"] == 0
    assert result["skipped"] == 1
    assert runtime._STATE["last_batch"]["failures"] == []
    assert runtime._STATE["last_batch"]["deferrals"][0]["symbol"] == "TEST"
    assert runtime._STATE["last_error"] is None


def test_strategy_validation_sweep_rotates_and_stays_fail_closed(monkeypatch):
    monkeypatch.setattr("strategy_lab.production.IMPLEMENTED_STRATEGIES", {"time_series_momentum"})
    monkeypatch.setattr("strategy_lab.production.backtest", lambda *_args, **_kwargs: {
        "ok": True,
        "point_in_time_status": "EXACT",
        "corporate_actions_verified": False,
        "validation": {"status": "COMPLETED", "economic_gates_passed": False},
        "persistence": {"ok": True, "status": "PERSISTED"},
    })
    runtime._STATE["strategy_validation_cursor"] = 0
    result = runtime.sweep_strategy_validation()
    assert result["ok"] is True
    assert result["strategy_id"] == "time_series_momentum"
    assert result["point_in_time_status"] == "EXACT"
    assert result["corporate_actions_verified"] is False
    assert result["economic_gates_passed"] is False
