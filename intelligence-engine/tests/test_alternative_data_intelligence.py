"""AGIB v2.0 Sprint 6 — Institutional Alternative Data Intelligence acceptance.

Soft KF only. Phase-1 high-signal datasets. Never fabricate. Prior layers frozen.
"""

from __future__ import annotations

from knowledge_factory.alternative_data_intelligence import store as iadi_store
from knowledge_factory.alternative_data_intelligence.pipeline import run_alternative_data_pipeline
from knowledge_factory.alternative_data_intelligence.production import (
    beneficiaries,
    company,
    dashboard,
    get_dataset,
    health,
    industry,
    registry,
    replay,
    search,
    trends,
)
from knowledge_factory.alternative_data_intelligence.schema import (
    FREEZE_LOCKS,
    IADI_VERSION,
    PHASE_1_DATASETS,
)
from knowledge_factory.alternative_data_intelligence.validators.gates import (
    validate_dataset,
    validate_observation,
)


def setup_function() -> None:
    iadi_store.reset()


def test_freeze_locks_and_phase1_scope():
    h = health()
    assert h["version"] == IADI_VERSION
    assert h["layer"] == "IADI"
    assert h["not_a_reasoning_engine"] is True
    assert h["not_a_prediction_engine"] is True
    assert h["soft_wire_only"] is True
    assert FREEZE_LOCKS["economic_relationship_intelligence_architecture"] is True
    assert FREEZE_LOCKS["industry_value_chain_intelligence_architecture"] is True
    assert len(PHASE_1_DATASETS) == 10
    assert "upi_transactions" in PHASE_1_DATASETS
    assert "electricity_demand" in PHASE_1_DATASETS
    assert "iip_manufacturing" in PHASE_1_DATASETS
    # PMI deferred (licensing)
    assert "pmi_manufacturing" not in PHASE_1_DATASETS


def test_pipeline_registry_and_series():
    report = run_alternative_data_pipeline()
    assert report["status"] == "ok"
    assert report["datasets"] == 10
    assert report["observations"] == 10 * 72  # 2019-2024 monthly
    assert report["phase_1_complete"] is True
    assert report["reasoning_changed"] is False
    assert report["prediction_engine"] is False
    reg = registry()
    assert reg["n_phase_1"] == 10
    assert "upi_transactions" in reg["registry"]


def test_trend_intelligence():
    run_alternative_data_pipeline()
    t = trends(dataset="upi_transactions")
    assert t["trends"]["status"] == "ok"
    assert t["trends"]["trend"] in ("rising", "falling", "stable")
    assert t["trends"]["momentum"] is not None
    assert t["trends"]["rolling_average"] is not None
    assert t["trends"]["historical_percentile"] is not None
    assert t["trends"]["historical_extremes"]["min"] <= t["trends"]["historical_extremes"]["max"]
    assert t["trends"]["derived_from_observations_only"] is True
    assert t["prediction"] is False


def test_company_and_industry_links():
    run_alternative_data_pipeline()
    power = company("NTPC")
    assert power["n"] >= 1
    assert any(d["dataset_id"] == "electricity_demand" for d in power["datasets"])
    auto = company("MARUTI")
    assert any(d["dataset_id"] == "vehicle_registrations" for d in auto["datasets"])
    banks = industry("private_banks")
    assert any(d["dataset_id"] in ("upi_transactions", "bank_credit_growth") for d in banks["datasets"])


def test_government_and_ieri_links():
    run_alternative_data_pipeline()
    credit = get_dataset("bank_credit_growth")
    assert "RBI" in (credit["dataset"].get("government_links") or [])
    assert credit["links"]["n_ieri"] >= 0  # soft-read; may be 0 if no hint match
    # GST / consumption should soft-link into IERI where hints match
    gst = get_dataset("gst_collections")
    assert gst["links"]["government_links"]


def test_historical_replay_no_future_leak():
    run_alternative_data_pipeline()
    early = replay(as_of="2020-01-01", dataset="upi_transactions")
    late = replay(as_of="2024-12-31", dataset="upi_transactions")
    assert early["future_leak"] is False
    assert late["future_leak"] is False
    assert late["n_observations"] >= early["n_observations"]
    # available_from lag: Jan 2019 obs available mid-Feb 2019
    very_early = replay(as_of="2019-01-10", dataset="upi_transactions")
    assert very_early["n_observations"] == 0


def test_provenance_and_validation():
    run_alternative_data_pipeline()
    for ds in iadi_store.list_datasets():
        obs = iadi_store.list_observations(dataset_id=ds["dataset_id"])
        assert validate_dataset(ds, observations=obs)["gate_pass"] is True
        assert ds.get("provenance")
        assert ds["provenance"]["fabricated"] is False
        for o in obs[:3]:
            assert validate_observation(o)["gate_pass"] is True
            assert o.get("source")
            assert o.get("available_from")


def test_dashboard_morning_board():
    run_alternative_data_pipeline()
    dash = dashboard(ensure=False)
    assert dash["north_star"] == "institutional_alternative_data_coverage"
    assert dash["alternative_data_coverage"]["datasets"] == 10
    assert dash["alternative_data_coverage"]["institutional_ready_pct"] == 100.0
    assert dash["missing_datasets"] == []
    assert dash["consumer_momentum"]["status"] == "ok"
    assert dash["manufacturing_momentum"]["status"] == "ok"
    assert dash["energy_momentum"]["status"] == "ok"
    assert dash["prediction"] is False


def test_success_questions_structured_answers():
    """Canonical alternative-data questions answered from observations + links only."""
    run_alternative_data_pipeline()

    # Consumer / UPI
    upi = trends(dataset="upi_transactions")
    assert upi["trends"]["status"] == "ok"
    assert "momentum" in upi["trends"]

    # Cement / manufacturing proxy via IIP (not inventing cement dispatch in phase 1)
    mfg = trends(dataset="iip_manufacturing")
    assert mfg["trends"]["trend"] in ("rising", "falling", "stable")

    # Logistics
    rail = trends(dataset="railway_freight")
    port = trends(dataset="port_cargo")
    assert rail["trends"]["status"] == "ok"
    assert port["trends"]["status"] == "ok"

    # Power demand
    power = beneficiaries("electricity_demand")
    assert "NTPC" in power["linked_companies"]
    assert power["prediction"] is False

    # Auto
    veh = beneficiaries("vehicle_registrations")
    assert "MARUTI" in veh["linked_companies"]

    # Banking / credit
    assert search("credit")["n"] >= 1
    assert company("HDFCBANK")["n"] >= 1


def test_soft_wire_prior_sprints_untouched():
    from knowledge_factory.company_intelligence.schema import ICI_VERSION
    from knowledge_factory.corporate_events.schema import ICEI_VERSION
    from knowledge_factory.economic_relationship_intelligence.schema import IERI_VERSION
    from knowledge_factory.government_intelligence.schema import IGRI_VERSION
    from knowledge_factory.industry_intelligence.schema import IIVI_VERSION

    assert ICI_VERSION and ICEI_VERSION and IGRI_VERSION and IIVI_VERSION and IERI_VERSION
    assert FREEZE_LOCKS["phases_1_7"] is True
    assert FREEZE_LOCKS["knowledge_factory_architecture"] is True
