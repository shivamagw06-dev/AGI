from macro_intelligence_engine.g20_source_catalog import COUNTRY_SOURCES, MODULES, catalogue
from macro_intelligence_engine.public_data import CORE_50, g20_matrix, g20_source_plan, latest_observations, readiness
import json

from macro_intelligence_engine.public_ingestion import WORLD_BANK_SERIES, YAHOO_MACRO_MARKET_SERIES, _web_semantically_matches, collect_web_macro_gaps, collect_yahoo_macro_market, registry_rows


def test_core_50_is_unique_and_complete():
    ids = [row[0] for row in CORE_50]
    assert len(ids) == 50
    assert len(set(ids)) == 50


def test_empty_warehouse_is_data_building(monkeypatch):
    monkeypatch.setattr("macro_intelligence_engine.public_data._warehouse_rows", lambda *_args, **_kwargs: [])
    result = readiness("India")
    assert result["observed"] == 0
    assert result["coverage_percent"] == 0
    assert result["status"] == "RED / NON-OPERATIONAL"
    assert result["mapped_but_empty"] == 0
    assert result["unmapped"] == 50
    assert result["evidence_validated"] == 0
    assert result["pit_validated"] == 0
    assert result["interpretation_readiness"] == "BLOCKED"


def test_registry_maps_every_core_series():
    rows = registry_rows()
    assert len(rows) == 50
    assert {row["series_id"] for row in rows} == {row[0] for row in CORE_50}
    assert all(row["license_class"] == "PUBLIC_OFFICIAL" for row in rows)
    assert len(WORLD_BANK_SERIES) >= 8


def test_yahoo_macro_market_is_limited_to_market_observations():
    assert set(YAHOO_MACRO_MARKET_SERIES) == {"usd_fx", "oil", "gas", "copper", "gold", "global_risk"}
    forbidden = {"gdp", "gdp_growth", "cpi", "core_cpi", "policy_rate", "government_debt_gdp", "unemployment"}
    assert forbidden.isdisjoint(YAHOO_MACRO_MARKET_SERIES)


def test_yahoo_macro_market_persists_tier_d_fetch_vintages(monkeypatch):
    payload = json.dumps({"chart": {"result": [{"timestamp": [1704067200, 1704153600], "indicators": {"quote": [{"close": [100.0, 101.0]}]}}]}}).encode()

    class Response:
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        def read(self): return payload

    captured = {}
    monkeypatch.setattr("macro_intelligence_engine.public_ingestion.urllib.request.urlopen", lambda *_args, **_kwargs: Response())
    monkeypatch.setattr("macro_intelligence_engine.public_ingestion._rest", lambda *_args, **_kwargs: [])
    monkeypatch.setattr("macro_intelligence_engine.public_ingestion._persist_official_run", lambda source, registry, observations, errors: captured.update(source=source, registry=registry, observations=observations, errors=errors) or {"ok": True, "accepted": len(observations)})
    result = collect_yahoo_macro_market()
    assert result["accepted"] == 12
    assert captured["registry"] == []
    assert captured["errors"] == []
    assert all(row["metadata"]["source_tier"] == "D" for row in captured["observations"])
    assert all(row["metadata"]["pit_status"] == "FETCH_VINTAGE_ONLY" for row in captured["observations"])
    assert all(row["metadata"]["history_range"] == "2y" for row in captured["observations"])


def test_latest_observations_returns_a_payload(monkeypatch):
    monkeypatch.setattr("macro_intelligence_engine.public_data._warehouse_rows", lambda *_args, **_kwargs: [])
    result = latest_observations("India")
    assert result["ok"] is True
    assert result["observations"] == []
    assert result["pit_status"] == "PIT LIMITED"


def test_g20_harmonized_layer_blocks_intelligence_claims(monkeypatch):
    monkeypatch.setattr("macro_intelligence_engine.public_data._warehouse_rows", lambda *_args, **_kwargs: [])
    result = g20_matrix()
    assert result["calculation_gate"] == "BLOCKED"
    assert "macro_regimes" in result["blocked_outputs"]
    assert result["source_tier_mix"] == {"A": 0, "B": 0, "C": 0, "D": 0}
    assert result["critical_5"] == {"observed": 0, "total": 95, "coverage_percent": 0.0}
    assert result["evidence_validated"] == 0
    assert result["pit_validated"] == 0


def test_g20_source_catalogue_covers_every_economy_and_module():
    rows = catalogue()
    assert len(COUNTRY_SOURCES) == 19
    assert len(MODULES) == 9
    assert len(rows) == 171
    assert len({row["catalogue_id"] for row in rows}) == 171
    assert all(row["source_priority"] == "S1_OFFICIAL_PRIMARY" for row in rows)
    assert all(row["pit_required"] is True for row in rows)


def test_g20_source_plan_does_not_treat_catalogue_as_evidence(monkeypatch):
    monkeypatch.setattr("macro_intelligence_engine.public_data._warehouse_rows", lambda *_args, **_kwargs: [])
    result = g20_source_plan()
    assert result["cells"] == 171
    assert result["status_counts"] == {"PLANNED": 171}
    assert result["calculation_gate"] == "BLOCKED"


def test_public_warehouse_reader_paginates_rest_results(monkeypatch):
    from macro_intelligence_engine import public_data

    public_data._PUBLIC_CACHE.clear()
    calls = []
    def fake_rest(_table, query=""):
        calls.append(query)
        if "offset=0" in query: return [{"id": index} for index in range(1000)]
        if "offset=1000" in query: return [{"id": index} for index in range(1000, 1500)]
        return []
    monkeypatch.setattr("macro_intelligence_engine.public_ingestion._rest", fake_rest)
    rows = public_data._warehouse_rows("macro_public_observations", limit=5000)
    assert len(rows) == 1500
    assert len(calls) == 2


def test_g20_reader_isolates_indicator_families(monkeypatch):
    from macro_intelligence_engine import public_data
    from macro_intelligence_engine.public_ingestion import G20_WORLD_BANK_SERIES

    public_data._PUBLIC_CACHE.clear()
    calls = []

    def fake_rest(_table, query=""):
        calls.append(query)
        for indicator in G20_WORLD_BANK_SERIES:
            if f"g20_*_{indicator}" in query:
                return [{"series_id": f"g20_ind_{indicator}", "country_code": "IND"}]
        return []

    monkeypatch.setattr("macro_intelligence_engine.public_ingestion._rest", fake_rest)
    rows = public_data._g20_observation_rows()

    assert len(rows) == len(G20_WORLD_BANK_SERIES)
    assert len(calls) == len(G20_WORLD_BANK_SERIES)
    assert all("series_id=like.g20_*_" in query for query in calls)


def test_world_bank_refresh_is_incremental_when_history_exists(monkeypatch):
    from macro_intelligence_engine.public_ingestion import collect_world_bank

    histories = []
    monkeypatch.setattr("macro_intelligence_engine.public_ingestion._series_has_history", lambda _series_id: True)
    monkeypatch.setattr(
        "macro_intelligence_engine.public_ingestion._wb_fetch",
        lambda _country, _indicator, history=25: histories.append(history) or ([], "hash", "url"),
    )
    monkeypatch.setattr("macro_intelligence_engine.public_ingestion._rest", lambda *_args, **_kwargs: [])

    result = collect_world_bank()

    assert result["ok"] is False
    assert histories == [3] * len(WORLD_BANK_SERIES)


def test_web_macro_fallback_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("MIE_WEB_FALLBACK_ENABLED", raising=False)
    result = collect_web_macro_gaps()
    assert result["status"] == "DISABLED"
    assert result["accepted"] == 0


def test_web_macro_fallback_persists_only_proposed_tier_d_evidence(monkeypatch):
    monkeypatch.setenv("MIE_WEB_FALLBACK_ENABLED", "true")
    monkeypatch.setenv("EXA_API_KEY", "test")
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setattr(
        "macro_intelligence_engine.public_ingestion._missing_india_series",
        lambda: [("cpi", "inflation", "Headline CPI", "monthly")],
    )
    monkeypatch.setattr("macro_intelligence_engine.public_ingestion._purge_invalid_web_candidates", lambda: [])
    monkeypatch.setattr(
        "macro_intelligence_engine.public_ingestion._exa_macro_search",
        lambda *_args: ([{"title":"MoSPI CPI release","url":"https://www.mospi.gov.in/cpi","published_date":"2026-08-12","text":"CPI was 2.1%."}], "query", "hash"),
    )
    monkeypatch.setattr(
        "macro_intelligence_engine.public_ingestion._extract_macro_observation",
        lambda *_args: ({"value":2.1,"unit":"%","period_date":"2026-07-31","release_date":"2026-08-12","source_url":"https://www.mospi.gov.in/cpi","source_title":"MoSPI CPI release","quote":"CPI was 2.1%.","confidence":0.94}, "gpt-test"),
    )
    captured={}
    monkeypatch.setattr(
        "macro_intelligence_engine.public_ingestion._persist_official_run",
        lambda source, registry, observations, errors: captured.update(source=source,observations=observations,errors=errors) or {"ok":True,"accepted":len(observations)},
    )
    result=collect_web_macro_gaps()
    row=captured["observations"][0]
    assert result["accepted"] == 1
    assert row["quality_status"] == "PROVISIONAL"
    assert row["metadata"]["source_tier"] == "D"
    assert row["metadata"]["trust_status"] == "PROPOSED"
    assert row["metadata"]["pit_status"] == "FETCH_VINTAGE_ONLY"


def test_web_semantic_guard_rejects_annual_growth_as_gdp_qoq():
    annual={"source_title":"Provisional estimates of annual GDP","quote":"Real GDP grew 7.8 percent in 2025-26."}
    quarterly={"source_title":"Quarterly GDP release","quote":"GDP increased 1.7% quarter-on-quarter (QoQ)."}
    assert _web_semantically_matches("gdp_qoq",annual) is False
    assert _web_semantically_matches("gdp_qoq",quarterly) is True
