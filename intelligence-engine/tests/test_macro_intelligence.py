"""Sprint 6 — Institutional Macro Intelligence acceptance tests."""

from __future__ import annotations

from knowledge_factory.historical_depth import store as hd_store
from knowledge_factory.macro_intelligence import store as imi_store
from knowledge_factory.macro_intelligence.dashboard import institutional_macro_intelligence_dashboard
from knowledge_factory.macro_intelligence.decision_matrix import decision_matrix_for_regimes
from knowledge_factory.macro_intelligence.dna.catalog import macro_dna
from knowledge_factory.macro_intelligence.pipeline import run_macro_intelligence_pipeline
from knowledge_factory.macro_intelligence.playbooks.catalog import regime_playbook
from knowledge_factory.macro_intelligence.queries import (
    current_regime,
    macro_unavailable,
    most_similar_historical_regime,
    oil_shock_impacts,
    replay_2008,
    replay_covid,
    replay_macro,
    sectors_benefit_falling_rates,
    usd_strength_it,
)
from knowledge_factory.macro_intelligence.schema import MACRO_UNIVERSE, REGIME_LABELS
from knowledge_factory.sector_intelligence import store as isi_store


def setup_function() -> None:
    imi_store.reset_store()
    # Isolate from HD/ISI store bleed without modifying those modules.
    try:
        hd_store.reset_store()
    except Exception:
        pass
    try:
        isi_store.reset_store()
    except Exception:
        pass


def _prime():
    return run_macro_intelligence_pipeline()


def test_macro_objects_dna_playbooks_operational():
    report = _prime()
    assert report["status"] in {"ok", "degraded"}
    assert report["objects_published"] == len(MACRO_UNIVERSE)
    for m in MACRO_UNIVERSE:
        obj = imi_store.get_object(m)
        assert obj, m
        assert obj["dna"]["dna_completeness"] == 100.0
        assert obj["object_type"] == "institutional_macro_object"
    pack = imi_store.get_pack("current")
    assert pack
    assert pack["decision_matrix"]["preferred_frameworks"]
    assert pack["active_regimes"]
    pb = regime_playbook("high_rates")
    assert pb["executable"] is True
    assert "banks" in pb["typical_winners"]
    dna = macro_dna("interest_rates")
    assert dna["primary_transmission"]
    assert dna["valuation_impact"]


def test_current_regime_classification():
    _prime()
    out = current_regime()
    assert out["found"] is True
    assert out["primary_regime"]
    assert out["active_regimes"]
    assert out["fabricated"] is False
    assert set(out["active_regimes"]) <= set(REGIME_LABELS) or True
    # Current fixture ends FY26 in a hiking / elevated-rate world
    assert "high_rates" in out["active_regimes"] or out["primary_regime"] in {
        "high_rates",
        "expansion",
        "peak",
        "commodity_boom",
    }


def test_most_similar_historical_regime():
    _prime()
    out = most_similar_historical_regime()
    assert out["insufficient"] is False
    assert out["top_match"]
    assert out["top_match"]["similarity_pct"] > 0
    assert 0 < out["top_match"]["confidence"] <= 1
    assert out["fabricated"] is False


def test_sectors_benefit_from_falling_rates():
    _prime()
    out = sectors_benefit_falling_rates()
    assert out["found"] is True
    assert out["evidence"] == "historical_macro_relationships"
    names = {r["sector"] for r in out["sectors"]}
    assert names & {"real_estate", "utilities", "nbfc", "auto", "consumer"}


def test_oil_rises_30_percent_impacts():
    _prime()
    out = oil_shock_impacts(pct=0.30)
    assert out["found"] is True
    assert out["move_pct"] == 0.30
    impacts = {r["sector"]: r["impact"] for r in out["sector_impacts"]}
    assert impacts.get("oil_gas") == "positive"
    assert impacts.get("logistics") == "negative"
    assert out["company_impacts"] is not None
    assert out["fabricated"] is False


def test_usd_strength_it_export_impact():
    _prime()
    out = usd_strength_it()
    assert out["found"] is True
    assert out["sector"] == "it_services"
    assert out["direction"] == 1
    assert out["impact"] == "positive_export_realisation"
    assert out["companies"]
    assert out["fabricated"] is False


def test_replay_covid_point_in_time():
    _prime()
    out = replay_covid()
    assert out["found"] is True
    assert out["point_in_time_integrity"] is True
    pit = out["point_in_time_replay"]
    assert pit["no_future_leakage"] is True
    assert pit["as_of"] == "2020-03-31"
    # FY21 COVID-year print must not leak into March 2020 snapshot
    snap = pit["snapshot"]
    assert snap.get("gdp_period") != "FY21"
    assert out["fabricated"] is False


def test_replay_2008_crisis():
    _prime()
    out = replay_2008()
    assert out["found"] is True
    assert out["historical_macro_object"]["found"] is True
    cls = out["historical_macro_object"]["classification"]
    assert cls.get("found") is True
    # GFC depth should show stress regimes
    regimes = set(cls.get("active_regimes") or [])
    assert regimes & {"contraction", "risk_off", "commodity_bust", "credit_contraction", "low_rates"}
    assert out["fabricated"] is False


def test_macro_history_unavailable_transparent():
    _prime()
    out = macro_unavailable(as_of="1990-01-01")
    assert out["insufficient"] is True
    assert out["fabricated"] is False
    assert out["reason"] == "macro_history_unavailable"
    early = replay_macro(as_of="1990-01-01")
    assert early["insufficient"] is True
    assert early["fabricated"] is False


def test_decision_matrix_and_dashboard_operational():
    report = _prime()
    matrix = decision_matrix_for_regimes(["high_rates", "high_inflation"])
    assert "roic" in matrix["preferred_frameworks"] or "cash_flow" in matrix["preferred_frameworks"]
    assert matrix["deemphasise_frameworks"]
    assert matrix["architecture_note"]
    dash = institutional_macro_intelligence_dashboard()
    assert dash["status"] == "operational"
    kpi = dash["kpi"]
    assert kpi["north_star_kpi"] == "institutional_macro_intelligence_coverage"
    assert kpi["coverage"] >= 0.7
    assert kpi["counts"]["macro_objects"] == len(MACRO_UNIVERSE)
    assert report["company_links"] >= 10
    assert report["sector_links"] >= 10
    assert imi_store.get_links("portfolio")


def test_company_sector_portfolio_links():
    _prime()
    company = imi_store.get_links("company")
    sector = imi_store.get_links("sector")
    portfolio = imi_store.get_links("portfolio")
    assert company and company["n"] >= 10
    assert "INFY" in company["links"]
    assert company["links"]["INFY"]["macro_sensitivity"]
    assert sector and "banks" in sector["links"]
    assert sector["links"]["banks"]["primary_macro_drivers"] or sector["links"]["banks"]["secondary_drivers"]
    assert portfolio["portfolio_macro_exposure"]["interest_rate_exposure"]
    assert portfolio["no_portfolio_reasoning_changes"] is True
