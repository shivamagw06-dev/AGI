from macro_intelligence_engine.public_data import CORE_50, readiness
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
    assert result["status"] == "DATA BUILDING"


def test_registry_maps_every_core_series():
    rows = registry_rows()
    assert len(rows) == 50
    assert {row["series_id"] for row in rows} == {row[0] for row in CORE_50}
    assert all(row["license_class"] == "PUBLIC_OFFICIAL" for row in rows)
    assert len(WORLD_BANK_SERIES) >= 8
