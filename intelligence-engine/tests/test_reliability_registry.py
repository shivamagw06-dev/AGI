from reliability_registry import component, registry


def test_registry_is_execution_authority():
    row = component("alpha")
    assert row["lifecycle"] == "operational"
    assert row["execution"] == "blocked"
    assert row["historical_performance_claims"] is False
    assert row["promotion_authority"] == "reliability_registry"


def test_health_is_separate_from_lifecycle_and_blocks_claims():
    row = component("value", health="degraded", health_reason="fundamentals stale")
    assert row["lifecycle"] == "operational"
    assert row["health"] == "degraded"
    assert row["execution"] == "blocked"
    assert row["automatic_demotion"] is True


def test_registry_contains_models_scanners_live_and_forecasts():
    body = registry()
    ids = {row["component_id"] for row in body["components"]}
    assert {"alpha", "live_alpha", "fie", "fle", "long_short_equity"} <= ids
    assert body["execution_allowed"] == 0


def test_runtime_registry_automatically_demotes_missing_inputs(monkeypatch):
    monkeypatch.setattr("hedge_fund_lab.terminal.universe_meta", lambda: {"count": 0})
    monkeypatch.setattr("hedge_fund_lab.terminal._universe", lambda: [])
    monkeypatch.setattr("hedge_fund_lab.terminal.fetch_live_alpha_rows", lambda limit=1: {"meta": {}})
    monkeypatch.setattr("hedge_fund_lab.terminal._forecast_intelligence_status", lambda: {"company_forecasts": 0, "outcome_evaluations": 0})
    from hedge_fund_lab.terminal import reliability_status

    body = reliability_status()
    rows = {row["component_id"]: row for row in body["components"]}
    assert rows["value"]["health"] == "failed"
    assert rows["live_alpha"]["health"] == "degraded"
    assert rows["fie"]["health"] == "degraded"
    assert rows["fle"]["health"] == "degraded"
