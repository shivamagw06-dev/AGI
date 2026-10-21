"""AGIB v2.0 Sprint 4 — Institutional Industry & Value Chain Intelligence acceptance.

Soft KF only. Never fabricate. Prior sprints / Phase 1–7 frozen.
Economic Network Graph is a declared later sprint.
"""

from __future__ import annotations

from knowledge_factory.industry_intelligence import store as iivi_store
from knowledge_factory.industry_intelligence.objects.compile import (
    compile_all_industries,
    compile_industry,
)
from knowledge_factory.industry_intelligence.pipeline import run_industry_intelligence_pipeline
from knowledge_factory.industry_intelligence.production import (
    accounting,
    company_industry,
    dashboard,
    get_industry,
    health,
    kpis,
    playbook,
    search,
    valuation,
    value_chain,
)
from knowledge_factory.industry_intelligence.registry.catalog import build_company_industry_map
from knowledge_factory.industry_intelligence.schema import (
    FREEZE_LOCKS,
    FUTURE_ECONOMIC_NETWORK_GRAPH,
    IIVI_VERSION,
)
from knowledge_factory.industry_intelligence.validators.gates import validate_industry


def setup_function() -> None:
    iivi_store.reset()


def test_freeze_locks_and_naming():
    h = health()
    assert h["version"] == IIVI_VERSION
    assert h["layer"] == "IIVI"
    assert "Value Chain" in h["programme"] or "value" in h["programme"].lower()
    assert h["not_a_reasoning_engine"] is True
    assert h["freeze_locks"]["company_intelligence_architecture"] is True
    assert h["freeze_locks"]["government_intelligence_architecture"] is True
    assert h["freeze_locks"]["sector_intelligence_architecture"] is True
    assert FREEZE_LOCKS["never_fabricate"] is True
    assert FUTURE_ECONOMIC_NETWORK_GRAPH["name"] == "Economic Network Graph"


def test_every_nifty500_company_mapped():
    cmap = build_company_industry_map()
    assert len(cmap) == 500
    pack = compile_all_industries()
    assert pack["company_map_complete"] is True
    assert pack["unmapped_companies"] == []
    assert company_industry("INFY")["industry_id"] == "it_services"
    assert company_industry("HDFCBANK")["industry_id"] == "private_banks"
    assert company_industry("SBIN")["industry_id"] == "psu_banks"
    assert company_industry("ULTRACEMCO")["industry_id"] == "cement"


def test_it_services_institutional_depth():
    obj = compile_industry("it_services", members=["INFY", "TCS", "HCLTECH"])
    assert obj["institutional_ready"] is True
    mods = obj["modules"]
    assert mods["business_model"]["data"]["how_money_earned"]
    assert mods["value_chain"]["data"]
    assert "Utilisation" in mods["accounting"]["data"]["core_metrics"]
    assert mods["valuation"]["data"]["preferred_framework"]
    assert mods["kpis"]["data"]["core"]
    assert mods["macro"]["data"]
    assert mods["government"]["data"]["duplicated_data"] is False
    assert mods["cycles"]["data"]["phases"]
    assert mods["playbook"]["data"]["best_frameworks"]
    assert mods["knowledge_graph"]["data"]["future_economic_network_graph"] == "declared_later_sprint"
    assert validate_industry(obj)["gate_pass"] is True


def test_banks_accounting_language():
    priv = compile_industry("private_banks", members=["HDFCBANK"])
    metrics = priv["modules"]["accounting"]["data"]["core_metrics"]
    for m in ("NIM", "CASA", "GNPA", "CAR/CET1", "Credit Cost"):
        assert m in metrics
    assert "PB" in str(priv["modules"]["valuation"]["data"]["apply"])


def test_cement_and_steel_value_chains():
    cement = compile_industry("cement", members=["ULTRACEMCO"])
    steel = compile_industry("steel", members=["TATASTEEL"])
    assert any("Limestone" in str(s) or s.get("stage") == "raw_materials" for s in cement["modules"]["value_chain"]["data"])
    assert "iron_ore" in (steel["modules"]["supply_chain"]["data"].get("commodities") or [])
    assert "Realisation" in cement["modules"]["accounting"]["data"]["core_metrics"]
    assert "Spread" in steel["modules"]["accounting"]["data"]["core_metrics"]


def test_apis_module_views():
    compile_industry("it_services", members=["INFY"])
    compile_industry("private_banks", members=["HDFCBANK"])
    assert get_industry("it_services")["industry_id"] == "it_services"
    assert playbook("it_services")["module"] == "playbook"
    assert value_chain("it_services")["module"] == "value_chain"
    assert accounting("it_services")["module"] == "accounting"
    assert valuation("it_services")["module"] == "valuation"
    assert kpis("it_services")["module"] == "kpis"
    hits = search("bank")
    assert hits["n"] >= 1
    assert any(r["industry_id"] == "private_banks" for r in hits["results"])


def test_pipeline_dashboard_full_coverage():
    report = run_industry_intelligence_pipeline()
    assert report["companies_mapped"] == 500
    assert report["company_map_complete"] is True
    assert report["status"] == "ok"
    assert report["reasoning_changed"] is False
    assert report["future_economic_network_graph"] == "declared_later_sprint"
    dash = dashboard(ensure=False)
    assert dash["companies_mapped"] == 500
    assert dash["institutional_ready_pct"] == 100.0
    assert dash["value_chain_coverage_pct"] == 100.0
    assert dash["accounting_playbooks_pct"] == 100.0
    assert dash["future_roadmap"]["name"] == "Economic Network Graph"


def test_provenance_on_modules():
    obj = compile_industry("fmcg", members=["HINDUNILVR"])
    for name, mod in obj["modules"].items():
        assert mod.get("provenance"), name
        assert mod["provenance"]["fabricated"] is False


def test_soft_wire_prior_sprints_untouched():
    from knowledge_factory.company_intelligence.schema import ICI_VERSION
    from knowledge_factory.corporate_events.schema import ICEI_VERSION
    from knowledge_factory.government_intelligence.schema import IGRI_VERSION

    assert ICI_VERSION and ICEI_VERSION and IGRI_VERSION
    assert FREEZE_LOCKS["knowledge_factory_architecture"] is True
