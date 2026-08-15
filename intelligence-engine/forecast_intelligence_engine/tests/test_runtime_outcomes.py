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
