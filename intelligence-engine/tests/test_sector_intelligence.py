"""Sprint 5 — Institutional Sector Intelligence acceptance tests."""

from __future__ import annotations

from knowledge_factory.historical_depth import store as hd_store
from knowledge_factory.historical_depth.pipeline import run_historical_pipeline
from knowledge_factory.sector_intelligence import store as isi_store
from knowledge_factory.sector_intelligence.dashboard import sector_intelligence_dashboard
from knowledge_factory.sector_intelligence.dna.catalog import sector_dna
from knowledge_factory.sector_intelligence.pipeline import run_sector_intelligence_pipeline
from knowledge_factory.sector_intelligence.playbooks.catalog import sector_playbook
from knowledge_factory.sector_intelligence.queries import (
    get_playbook,
    is_expensive_vs_sector_history,
    sector_valuation_during,
    sectors_outperform_when_rates_fall,
    sectors_resembling_regime,
    should_use_dcf,
    strongest_roic_sector,
)
from knowledge_factory.sector_intelligence.schema import SECTOR_UNIVERSE


SEED_FOR_HD = [
    "INFY",
    "TCS",
    "WIPRO",
    "HCLTECH",
    "TECHM",
    "HDFCBANK",
    "ICICIBANK",
    "SBIN",
    "AXISBANK",
    "MARUTI",
    "TATAMOTORS",
    "HINDUNILVR",
    "ITC",
    "RELIANCE",
    "NTPC",
    "POWERGRID",
]


def setup_function() -> None:
    isi_store.reset_store()
    hd_store.reset_store()
    try:
        from knowledge_factory.macro_intelligence import store as imi_store

        imi_store.reset_store()
    except Exception:
        pass


def _prime():
    run_historical_pipeline(entities=SEED_FOR_HD)
    return run_sector_intelligence_pipeline()


def test_sector_objects_dna_playbooks_operational():
    report = _prime()
    assert report["status"] in {"ok", "degraded"}
    assert report["objects_published"] == len(SECTOR_UNIVERSE)
    for s in SECTOR_UNIVERSE:
        obj = isi_store.get_object(s)
        assert obj, s
        assert obj["sector_dna"]["dna_completeness"] == 100.0
        assert obj["sector_playbook"]["executable"] is True
        assert obj["valuation_framework_mapping"]["preferred_frameworks"]
        assert obj["macro_relationships"]["relationships"]
        assert isi_store.get_pack(s)


def test_infosys_expensive_relative_to_it_history():
    _prime()
    out = is_expensive_vs_sector_history("INFY", "it_services")
    assert out["found"] is True
    assert out["evidence"] == "historical_sector_valuation"
    assert out["fabricated"] is False
    assert out["company_pe"] is not None
    assert out["sector_historical_median_pe"] is not None
    assert "company_vs_sector_history_percentile" in out


def test_hdfc_bank_framework_rejects_traditional_dcf():
    _prime()
    out = should_use_dcf("HDFCBANK")
    assert out["found"] is True
    assert out["sector"] == "banks"
    assert out["residual_income_preferred"] is True
    assert out["primary_framework"] == "residual_income"
    assert "traditional_dcf" in out["forbidden_frameworks"]
    assert out["should_use_traditional_dcf"] is False
    assert "Residual Income" in out["recommendation"]


def test_sectors_outperform_when_rates_fall():
    _prime()
    out = sectors_outperform_when_rates_fall()
    assert out["found"] is True
    assert out["n"] >= 3
    names = {r["sector"] for r in out["sectors"]}
    # Auto / NBFC / real estate / utilities are classic beneficiaries
    assert names & {"auto", "nbfc", "real_estate", "utilities", "infrastructure"}


def test_it_sector_valuation_during_2008():
    _prime()
    out = sector_valuation_during("it_services", 2008)
    assert out["found"] is True
    assert out["source"] == "historical_sector_replay"
    assert out["valuation"]
    assert out["fabricated"] is False


def test_strongest_roic_sector_ranking():
    _prime()
    out = strongest_roic_sector()
    assert out["found"] is True
    assert out["sector"]
    assert out["evidence"] == "historical_ranking"
    assert len(out["ranking"]) >= 1


def test_sectors_resemble_rate_hiking_regime():
    _prime()
    out = sectors_resembling_regime("rate_hike_2022_23")
    assert out["found"] is True
    assert out["resembles"] == "rate_hiking_cycle"
    assert out["fabricated"] is False


def test_sector_history_unavailable_transparent():
    _prime()
    out = is_expensive_vs_sector_history("NOTAREALCO", "not_a_sector")
    assert out["found"] is False
    assert out["insufficient"] is True
    assert out["fabricated"] is False
    missing = sector_valuation_during("not_a_sector", 2008)
    assert missing["found"] is False
    assert missing["fabricated"] is False


def test_it_playbook_executable():
    pb = sector_playbook("it_services")
    assert pb["executable"] is True
    assert "AI adoption" in pb["primary_value_drivers"] or "ai_adoption" in str(pb["primary_value_drivers"]).lower()
    assert "attrition" in pb["watch_metrics"]
    assert pb["preferred_valuation"]
    assert get_playbook("banks")["found"] is True
    assert "residual_income" in sector_dna("banks")["preferred_frameworks"]


def test_sector_intelligence_dashboard_kpi():
    _prime()
    board = sector_intelligence_dashboard()
    assert board["north_star"] == "institutional_sector_intelligence_coverage"
    assert board["sector_coverage_pct"] == 100.0
    assert board["sector_dna_completeness"] == 100.0
    assert board["playbook_coverage_pct"] == 100.0
    assert board["framework_coverage_pct"] == 100.0
    assert board["macro_relationship_coverage_pct"] == 100.0
    assert board["average_evidence_quality"] >= 70.0
    assert board["roadmap_next"] == "macro_intelligence"
