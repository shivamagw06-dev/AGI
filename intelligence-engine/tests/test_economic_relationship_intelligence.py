"""AGIB v2.0 Sprint 5 — Institutional Economic Relationship Intelligence acceptance.

Soft KF only. Never fabricate. Prior sprints / Phase 1–7 frozen.
Graph is implementation detail; product is structured economic knowledge.
"""

from __future__ import annotations

from knowledge_factory.economic_relationship_intelligence import store as ieri_store
from knowledge_factory.economic_relationship_intelligence.pipeline import (
    run_economic_relationship_pipeline,
)
from knowledge_factory.economic_relationship_intelligence.production import (
    commodity,
    company,
    dashboard,
    health,
    industry,
    macro,
    network,
    path_query,
    policy,
    replay,
    search,
    shock_impact,
)
from knowledge_factory.economic_relationship_intelligence.schema import (
    ECONOMIC_SEMANTICS,
    FREEZE_LOCKS,
    IERI_VERSION,
    TYPE_TO_SEMANTICS,
)
from knowledge_factory.economic_relationship_intelligence.validators.gates import (
    validate_relationship,
)


def setup_function() -> None:
    ieri_store.reset()


def test_freeze_locks_and_semantics():
    h = health()
    assert h["version"] == IERI_VERSION
    assert h["layer"] == "IERI"
    assert h["not_a_reasoning_engine"] is True
    assert h["not_a_graph_database_project"] is True
    assert h["not_a_planner"] is True
    assert h["soft_wire_only"] is True
    assert FREEZE_LOCKS["industry_value_chain_intelligence_architecture"] is True
    assert FREEZE_LOCKS["government_intelligence_architecture"] is True
    assert FREEZE_LOCKS["company_intelligence_architecture"] is True
    assert set(h["economic_semantics"]) == set(ECONOMIC_SEMANTICS)
    assert TYPE_TO_SEMANTICS["supplier"] == "structural"
    assert TYPE_TO_SEMANTICS["policy_dependency"] == "policy"
    assert TYPE_TO_SEMANTICS["oil_sensitivity"] == "market"
    assert TYPE_TO_SEMANTICS["power_dependency"] == "operational"
    assert TYPE_TO_SEMANTICS["substitute_industry"] == "behavioural"
    assert TYPE_TO_SEMANTICS["credit_dependency"] == "financial"


def test_pipeline_registry_and_commodities():
    report = run_economic_relationship_pipeline()
    assert report["status"] == "ok"
    assert report["relationships"] >= 50
    assert report["commodities"] >= 19
    assert report["reasoning_changed"] is False
    assert report["planner_changed"] is False
    assert ieri_store.get_commodity("crude_oil")["name"] == "Crude Oil"
    assert ieri_store.get_commodity("semiconductors")["import_dependence"] == "very_high"


def test_company_links():
    run_economic_relationship_pipeline()
    d = company("DIXON")
    assert d["ticker"] == "DIXON"
    assert d["n"] >= 1
    # semiconductor import dependency
    imports = d["relationships"]["import_sources"] + d["relationships"]["commodity_inputs"]
    assert any(
        (x.get("counterpart") == "semiconductors" or "semiconductor" in str(x.get("counterpart")).lower())
        for x in imports
    )
    peers = company("INFY")
    assert peers["relationships"]["competitors"]


def test_industry_and_commodity_links():
    run_economic_relationship_pipeline()
    steel_ind = industry("passenger_vehicles")
    assert steel_ind["n"] >= 1
    oil = commodity("crude_oil")
    assert oil["commodity"]["commodity_id"] == "crude_oil"
    assert oil["n"] >= 1
    assert oil["transmission"]["first_order"]


def test_government_and_macro_links():
    run_economic_relationship_pipeline()
    pli = policy("PLI-ELECTRONICS")
    assert pli["n"] >= 1
    assert pli["companies"]
    assert pli["transmission"]["first_order"] is not None
    repo = macro("repo_rate")
    assert repo["n"] >= 1
    assert repo["transmission"]["second_order"] or repo["transmission"]["first_order"]


def test_supplier_customer_and_transmission():
    run_economic_relationship_pipeline()
    # Tata Steel → downstream industries
    ts = company("TATASTEEL")
    assert ts["n"] >= 1
    shock = shock_impact("crude_oil")
    assert shock["beneficiaries"] or shock["losers"]
    assert any("hurt" in str(x.get("shock_direction")) for x in shock["losers"]) or shock["losers"]
    # repo second-order path exists in graph
    paths = path_query(source="repo_rate", max_depth=3, limit=20)
    assert paths["n"] >= 1
    assert paths["reasoning"] is False


def test_network_path_search_replay():
    run_economic_relationship_pipeline()
    net = network("crude_oil", depth=2)
    assert net["n_edges"] >= 1
    assert net["reasoning"] is False
    hits = search("oil")
    assert hits["n"] >= 1
    early = replay(as_of="2014-06-01")
    late = replay(as_of="2024-01-01")
    assert early["future_leak"] is False
    assert late["n"] >= early["n"]
    # PLI available from 2020 — absent in 2019 replay
    pli_early = [r for r in early["relationships"] if "PLI" in str(r.get("source")) or "PLI" in str(r.get("target"))]
    pli_late = [
        r
        for r in late["relationships"]
        if "PLI" in str(r.get("source")) or "PLI" in str(r.get("target")) or "PLI" in str(r.get("relationship_id"))
    ]
    # at least late has PLI-related rows via entity filter on full store
    pli_rows = ieri_store.list_relationships(entity="PLI-ELECTRONICS", as_of="2019-01-01")
    assert pli_rows == []
    assert ieri_store.list_relationships(entity="PLI-ELECTRONICS", as_of="2021-01-01")


def test_provenance_and_validation():
    run_economic_relationship_pipeline()
    rows = ieri_store.list_relationships()
    assert rows
    for r in rows[:20]:
        assert r.get("provenance")
        assert r["provenance"]["fabricated"] is False
        assert r.get("source")
        assert r.get("semantics") in ECONOMIC_SEMANTICS
        assert validate_relationship(r)["gate_pass"] is True


def test_dashboard_morning_board():
    run_economic_relationship_pipeline()
    dash = dashboard(ensure=False)
    assert dash["north_star"] == "institutional_economic_relationship_coverage"
    assert dash["economic_relationship_coverage"]["relationships"] >= 50
    assert dash["commodity_coverage"]["commodities"] >= 19
    assert dash["company_relationships"] >= 1
    assert dash["industry_relationships"] >= 1
    assert dash["government_links"] >= 1
    assert dash["macro_links"] >= 1
    assert dash["relationship_confidence"]["average"] > 0


def test_success_questions_structured_answers():
    """Canonical relationship questions answered from stored edges only."""
    run_economic_relationship_pipeline()

    # Which companies benefit / lose if crude oil moves?
    oil = shock_impact("crude_oil")
    assert oil["beneficiaries"]
    assert oil["losers"]

    # Which industries depend on imported copper?
    copper = commodity("copper")
    assert any(r.get("relationship_type") == "import_dependency" for r in copper["relationships"]) or copper["n"] >= 1

    # Semiconductor import dependents
    semi = search("semiconductors", relationship_type="import_dependency")
    tickers = {r.get("source") for r in semi["results"]} | {r.get("target") for r in semi["results"]}
    assert "DIXON" in tickers

    # Railway capex beneficiaries
    rail = search("BUDGET-CAPEX")
    assert rail["n"] >= 1

    # Repo-rate indirect effects
    repo_tx = macro("repo_rate")["transmission"]
    assert repo_tx["first_order"]
    assert repo_tx["second_order"] or repo_tx["third_order"]

    # Steel price down → downstream industries
    steel = shock_impact("steel")
    assert steel["beneficiaries"] or commodity("steel")["transmission"]["first_order"]

    # PLI semiconductor / electronics orders
    pli = policy("PLI-ELECTRONICS")
    assert pli["transmission"]["first_order"]
    orders = {c.get("transmission_order") for c in pli["companies"]}
    assert 1 in orders


def test_soft_wire_prior_sprints_untouched():
    from knowledge_factory.company_intelligence.schema import ICI_VERSION
    from knowledge_factory.corporate_events.schema import ICEI_VERSION
    from knowledge_factory.government_intelligence.schema import IGRI_VERSION
    from knowledge_factory.industry_intelligence.schema import IIVI_VERSION

    assert ICI_VERSION and ICEI_VERSION and IGRI_VERSION and IIVI_VERSION
    assert FREEZE_LOCKS["knowledge_factory_architecture"] is True
    assert FREEZE_LOCKS["phases_1_7"] is True
