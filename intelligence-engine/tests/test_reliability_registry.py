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
