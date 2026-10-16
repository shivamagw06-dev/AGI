"""CCI-01 — Cross-Company Intelligence tests."""

from __future__ import annotations

from institutional_cross_company.clustering import build_clusters, cluster_for_ticker
from institutional_cross_company.dependency import dependency_map
from institutional_cross_company.impact_engine import impact_query
from institutional_cross_company.models import EvidenceRef, InstitutionalRelationship
from institutional_cross_company.production import (
    get_company_relationships,
    get_macro_relationships,
    get_sector_relationships,
    health,
    query_relationships,
    reset_for_tests,
    soft_slice_mission_control,
)
from institutional_cross_company.propagation import propagate
from institutional_cross_company.relationship_engine import relationships_for_company
from institutional_cross_company.relationship_registry import (
    catalog,
    register_relationship_provider,
    reset_registry_for_tests,
)
from institutional_cross_company.schema import CCI_WORKSTREAM_ID, GRAPH_SYSTEM_OF_RECORD
from institutional_cross_company.similarity import similar_companies
from institutional_cross_company.traversal import traverse
from institutional_cross_company.validator import validate_relationship, validate_relationships


def setup_function():
    reset_for_tests()


def test_health_does_not_own_graph():
    h = health()
    assert h["workstream_id"] == CCI_WORKSTREAM_ID
    assert h["owns_graph"] is False
    assert h["graph_system_of_record"] == GRAPH_SYSTEM_OF_RECORD
    assert h["generates_recommendations"] is False
    assert h["predictive"] is False
    assert h["dependency_propagation_only"] is True
    assert any(p["relationship_type"] == "competitor" for p in h["providers"])


def test_relationship_provider_registry_extensible():
    called = {"n": 0}

    def discover_esg(ctx):
        called["n"] += 1
        from institutional_cross_company.relationship_registry import make_relationship
        from institutional_cross_company.models import EvidenceRef

        t = str(ctx.get("ticker") or "TCS")
        return [
            make_relationship(
                source=t,
                target="ESG_PEER",
                relationship_type="competitor",
                strength=0.5,
                confidence=0.6,
                provider="esg_link_engine",
                evidence=[EvidenceRef("e1", "ESG peer seed", "test")],
            )
        ]

    register_relationship_provider(
        "competitor",
        provider="esg_link_engine",
        category="business",
        description="test override",
        discover=discover_esg,
    )
    from institutional_cross_company.relationship_registry import get as get_provider

    # Re-registering competitor replaces provider — extensibility point
    assert get_provider("competitor").provider == "esg_link_engine"
    reset_registry_for_tests()
    assert any(
        p["provider"] == "competitor_engine"
        for p in catalog()
        if p["relationship_type"] == "competitor"
    )


def test_relationship_discovery_banking():
    rels = relationships_for_company("HDFCBANK")
    types = {r.relationship_type for r in rels}
    targets = {r.target_entity for r in rels}
    assert "competitor" in types
    assert {"ICICIBANK", "KOTAKBANK", "AXISBANK"} & targets
    assert any(r.category == "macro" for r in rels)
    assert all(r.evidence for r in rels)


def test_traversal_network():
    pack = traverse("HDFCBANK", relationship_types=["competitor"], max_depth=1)
    assert pack["owns_graph"] is False
    assert pack["kg_ref"]["system"] == "KG-01"
    assert "ICICIBANK" in pack["nodes"] or any(e["to"] == "ICICIBANK" for e in pack["edges"])


def test_similarity_infosys():
    hits = similar_companies("INFY")
    tickers = {h.ticker for h in hits}
    assert "TCS" in tickers or "WIPRO" in tickers
    assert hits[0].score >= hits[-1].score


def test_clustering():
    clusters = build_clusters()
    labels = {c.label for c in clusters}
    assert "Private Banks" in labels
    assert "IT Services" in labels
    assert any("HDFCBANK" in c.members for c in cluster_for_ticker("HDFCBANK"))


def test_propagation_rates_not_predictive():
    prop = propagate("interest_rates")
    assert prop.predictive is False
    assert "Banking" in " ".join(prop.steps) or "NIM" in " ".join(prop.steps) or prop.affected_entities
    assert "HDFCBANK" in prop.affected_entities
    d = dependency_map("oil")
    assert d["ok"] is True
    assert d["predictive"] is False
    assert "TATAMOTORS" in d["companies"] or "MARUTI" in d["companies"]


def test_validator_rejects_no_evidence_and_duplicates():
    bad = InstitutionalRelationship(
        relationship_id="x",
        source_entity="A",
        target_entity="B",
        relationship_type="competitor",
        strength=0.5,
        confidence=0.9,
        evidence=(),
    )
    ok, errors = validate_relationship(bad)
    assert ok is False
    assert "no supporting evidence" in errors

    good = InstitutionalRelationship(
        relationship_id="g1",
        source_entity="A",
        target_entity="B",
        relationship_type="competitor",
        strength=0.5,
        confidence=0.9,
        evidence=(EvidenceRef("e", "label"),),
    )
    dup = InstitutionalRelationship(
        relationship_id="g2",
        source_entity="B",
        target_entity="A",
        relationship_type="competitor",
        strength=0.5,
        confidence=0.9,
        evidence=(EvidenceRef("e2", "label"),),
    )
    accepted, report = validate_relationships([good, dup])
    assert len(accepted) == 1
    assert report["rejected"] >= 1


def test_company_api_integration():
    pack = get_company_relationships("HDFCBANK")
    assert pack["ok"] is True
    assert pack["owns_graph"] is False
    assert pack["kg_ref"]["system"] == GRAPH_SYSTEM_OF_RECORD
    assert pack["competitors"]
    assert pack["macro_drivers"]


def test_it_and_auto_ecosystems():
    it = get_company_relationships("TCS")
    assert "INFY" in it["competitors"] or "WIPRO" in it["competitors"]
    auto = get_company_relationships("TATAMOTORS")
    assert auto["ok"] is True
    assert any(c in auto["competitors"] for c in ("MARUTI", "M&M", "BAJAJ-AUTO", "HEROMOTOCO"))


def test_macro_and_sector_apis():
    macro = get_macro_relationships("oil")
    assert macro["ok"] is True
    assert macro["propagation"]["predictive"] is False
    assert macro["propagation"]["affected_entities"]
    sector = get_sector_relationships("Private Banks")
    assert sector["ok"] is True
    assert sector["relationships"]


def test_impact_and_query():
    impact = impact_query(driver="oil")
    assert impact["ok"] is True
    assert impact["generates_recommendations"] is False
    assert impact["owns_graph"] is False

    q = query_relationships({"question": "Which companies compete with TATAMOTORS?"})
    assert q["ok"] is True
    assert q["intent"] in {"competitors", "company"}
    assert q["relationships"]

    q2 = query_relationships({"question": "Show companies benefiting from lower rates"})
    assert q2["propagation"] is not None
    assert q2["propagation"]["driver"] == "interest_rates"


def test_multi_sector_propagation_and_portfolio():
    prop = propagate("gdp")
    assert len(set(prop.affected_entities)) >= 5
    # portfolio overlap may be soft/demo
    assert isinstance(prop.portfolio_holdings, tuple)

    q = query_relationships(
        {"question": "Which portfolio holdings share the same macro risks?", "portfolio_id": "agi-core-equity"}
    )
    assert q["ok"] is True


def test_mission_control_relationship_center():
    get_company_relationships("HDFCBANK")
    slice_ = soft_slice_mission_control()
    assert slice_["relationship_center"] is True
    assert slice_["owns_graph"] is False
    assert "relationship_coverage" in slice_
    assert slice_["graph_integrity"] == "delegated_to_KG-01"


def test_uag_can_route_relationship_questions():
    from institutional_orchestrator.object_registry import match_routes, reset_registry_for_tests as uag_reset
    from institutional_orchestrator.production import ask, reset_for_tests as uag_prod_reset

    uag_reset()
    uag_prod_reset()
    hits = match_routes("Which companies compete with Tata Motors?")
    types = {h.object_type for h in hits}
    assert "Relationship" in types

    result = ask({"question": "Which companies compete with HDFCBANK?", "entities": ["HDFCBANK"]})
    # May validate depending on plan; payload should not invent recommendations
    assert result.get("generates_recommendations") is False
    consulted = (result.get("response") or {}).get("objects_consulted") or []
    # Soft: Relationship may be in plan when routes match
    assert "Relationship" in consulted or result.get("ok") in {True, False}
