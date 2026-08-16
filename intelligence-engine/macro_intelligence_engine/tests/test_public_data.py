from macro_intelligence_engine.g20_source_catalog import COUNTRY_SOURCES, MODULES, catalogue
from macro_intelligence_engine.public_data import CORE_50, g20_matrix, g20_source_plan, latest_observations, readiness
from macro_intelligence_engine.public_ingestion import WORLD_BANK_SERIES, registry_rows


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
