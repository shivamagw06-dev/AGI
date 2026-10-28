"""AGIB v2.0 Sprint 7 — Institutional Market Expectations Intelligence acceptance.

Phase-1: company guidance, actuals, AGIB forecasts. Phase-2 consensus modular.
Soft KF only. Never fabricate street consensus. Prior layers frozen.
"""

from __future__ import annotations

from knowledge_factory.market_expectations_intelligence import store as imei_store
from knowledge_factory.market_expectations_intelligence.collectors.consensus_licensed import (
    collect_licensed_consensus,
    licensed_consensus_available,
)
from knowledge_factory.market_expectations_intelligence.pipeline import (
    run_market_expectations_pipeline,
)
from knowledge_factory.market_expectations_intelligence.production import (
    company,
    dashboard,
    gap,
    health,
    narratives,
    registry,
    replay,
    revisions,
    search,
    surprises,
)
from knowledge_factory.market_expectations_intelligence.schema import (
    FREEZE_LOCKS,
    IMEI_VERSION,
    PHASE_1_SOURCES,
    UNKNOWN,
)
from knowledge_factory.market_expectations_intelligence.validators.gates import (
    validate_expectation,
)


def setup_function() -> None:
    imei_store.reset()


def test_freeze_locks_and_naming():
    h = health()
    assert h["version"] == IMEI_VERSION
    assert h["layer"] == "IMEI"
    assert "Expectations" in h["programme"]
    assert h["not_a_reasoning_engine"] is True
    assert h["not_a_prediction_engine"] is True
    assert h["not_broker_report_ingestion"] is True
    assert h["not_recommendation_aggregation"] is True
    assert h["not_sentiment_analysis"] is True
    assert h["soft_wire_only"] is True
    assert FREEZE_LOCKS["alternative_data_intelligence_architecture"] is True
    assert FREEZE_LOCKS["economic_relationship_intelligence_architecture"] is True
    assert FREEZE_LOCKS["phase_2_consensus_optional"] is True
    assert "company_guidance" in PHASE_1_SOURCES
    assert "agib_internal_forecast" in PHASE_1_SOURCES


def test_phase2_consensus_modular_unknown():
    assert licensed_consensus_available() is False
    c = collect_licensed_consensus(entity="INFY", metric="eps")
    assert c["status"] == "not_configured"
    assert c["consensus"]["median"] == UNKNOWN
    assert c["licensed_consensus"] is False
    assert c["expectations"] == []


def test_pipeline_registry_revisions_surprises():
    report = run_market_expectations_pipeline()
    assert report["status"] == "ok"
    assert report["expectations_ready"] >= 15
    assert report["revisions"] >= 2
    assert report["surprises"] >= 3
    assert report["narratives"] == 10
    assert report["reasoning_changed"] is False
    assert report["broker_reports_scraped"] is False
    assert report["phase_2_consensus"]["status"] == "not_configured"
    reg = registry()
    assert reg["delivery_phase"] == "phase_1_public_auditable"
    assert "licensed_consensus_feed" in reg["phase_2_sources"]


def test_infosys_beat_expectations():
    run_market_expectations_pipeline()
    g = gap("INFY")
    assert g["n"] >= 1
    assert any(x["beat_miss"] == "beat" for x in g["gaps"])
    eps = [x for x in g["gaps"] if x["metric"] == "eps"]
    assert eps
    assert eps[0]["actual"] > eps[0]["expectation"]
    assert g["prediction"] is False


def test_hdfc_consensus_revision_history():
    run_market_expectations_pipeline()
    revs = revisions(entity="HDFCBANK")
    assert revs["n"] >= 1
    assert any(r["direction"] in ("upgrade", "downgrade") for r in revs["revisions"])
    # six-month style replay window
    early = replay(as_of="2024-05-01", entity="HDFCBANK")
    late = replay(as_of="2024-08-01", entity="HDFCBANK")
    assert late["n_expectations"] >= early["n_expectations"]
    assert late["future_leak"] is False


def test_positive_revisions_and_surprises_api():
    run_market_expectations_pipeline()
    dash = dashboard(ensure=False)
    assert dash["largest_upward_revisions"] or dash["largest_downward_revisions"]
    sur = surprises()
    assert sur["n"] >= 1
    assert search("INFY")["n"] >= 1


def test_narratives_structured_themes():
    run_market_expectations_pipeline()
    n = narratives()
    assert n["n"] == 10
    assert n["not_news_summary"] is True
    ids = {x["narrative_id"] for x in n["narratives"]}
    assert "ai_spending" in ids
    assert "banking_credit_cycle" in ids
    assert "digitalisation" in ids
    ai = narratives("ai_spending")
    assert ai["narrative"]["affected_companies"]


def test_company_links_soft_not_duplicated():
    run_market_expectations_pipeline()
    c = company("INFY")
    assert c["n_expectations"] >= 1
    assert c["licensed_consensus_assumed"] is False
    # soft pointers only
    assert "links" in c
    assert c["surprises"]


def test_historical_replay_and_provenance():
    run_market_expectations_pipeline()
    early = replay(as_of="2024-06-01", entity="INFY")
    # July actuals must not leak
    assert all(str(e.get("available_from")) <= "2024-06-01" for e in early["expectations"])
    for e in imei_store.list_expectations(entity="INFY"):
        if e.get("forecast_value") == UNKNOWN:
            continue
        assert e.get("provenance")
        assert e["provenance"]["fabricated"] is False
        if (e.get("validation") or {}).get("status") == "pass":
            assert validate_expectation(e)["gate_pass"] is True


def test_dashboard_morning_board():
    run_market_expectations_pipeline()
    dash = dashboard(ensure=False)
    assert dash["north_star"] == "institutional_market_expectations_coverage"
    assert dash["expectation_dashboard"]["surprises"] >= 1
    assert dash["expectation_dashboard"]["narratives"] == 10
    assert dash["consensus_confidence"]["licensed_consensus"] is False
    assert dash["unknown_expectations"] >= 1  # phase-2 placeholder
    assert dash["prediction"] is False


def test_success_questions():
    run_market_expectations_pipeline()
    # Did Infosys beat?
    assert any(g["beat_miss"] == "beat" for g in gap("INFY")["gaps"])
    # HDFC revisions
    assert revisions(entity="HDFCBANK")["n"] >= 1
    # Strongest positive revisions exist on board
    dash = dashboard(ensure=False)
    assert isinstance(dash["largest_upward_revisions"], list)
    # Narratives strengthening/weakening tracked
    assert narratives()["narrative_changes"]
    # Repeated outperformance flag computed (may be false — still present)
    assert "repeated_outperformance" in gap("INFY")


def test_soft_wire_prior_sprints_untouched():
    from knowledge_factory.alternative_data_intelligence.schema import IADI_VERSION
    from knowledge_factory.company_intelligence.schema import ICI_VERSION
    from knowledge_factory.economic_relationship_intelligence.schema import IERI_VERSION
    from knowledge_factory.government_intelligence.schema import IGRI_VERSION
    from knowledge_factory.industry_intelligence.schema import IIVI_VERSION

    assert all([ICI_VERSION, IGRI_VERSION, IIVI_VERSION, IERI_VERSION, IADI_VERSION])
    assert FREEZE_LOCKS["phases_1_7"] is True
    assert FREEZE_LOCKS["knowledge_factory_architecture"] is True
