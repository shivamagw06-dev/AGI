from forecast_learning_engine.snapshot import build_snapshot


def test_snapshot_is_deterministic_and_tracks_cutoff():
    bundle = {
        "symbol": "INFY",
        "annual": [{"fiscal_year": "FY25", "revenue": 100, "last_updated": "2026-06-01T00:00:00Z"}],
        "quarterly": [],
        "historical_valuation": [{"date": "2026-07-01", "pe": 20}],
        "valuation_ratios": [],
        "consensus": [],
        "rie": {"ok": True},
        "research_timeline": [],
        "mie": {},
        "mie_scenarios": {},
    }
    first = build_snapshot(bundle, generated_at="2026-08-13T00:00:00Z", engine_version="8.5")
    second = build_snapshot(bundle, generated_at="2026-08-13T00:00:00Z", engine_version="8.5")
    assert first == second
    assert first["data_cutoff_timestamp"] == "2026-06-01T00:00:00Z"
    assert first["input_manifest"]["financial"]["rows"] == 1
    assert len(first["financial_data_version"]) == 20
