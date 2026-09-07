"""Sprint 11.3 — Sector Relationship Intelligence tests."""

from __future__ import annotations

from sector_relationship_intelligence import traces
from sector_relationship_intelligence.production import (
    dashboard,
    for_company,
    for_sector,
    graph,
    health,
    relationships,
    run,
    search,
)
from sector_relationship_intelligence.schema import NO_SRI_ACTIONS
from sector_relationship_intelligence.store import reset


def setup_function() -> None:
    reset()
    traces.clear()


def test_sri_health() -> None:
    h = health()
    assert h["status"] == "ok"
    assert h["programme_short"] == "SRI"
    assert h["phase"] == "11.3"
    assert h["ask_triggers_collection"] is False
    assert h["providers_queried_always"] == []
    for item in NO_SRI_ACTIONS:
        assert item in h["does_not"]


def test_read_never_rebuilds() -> None:
    out = relationships()
    assert out["n"] == 0
    assert out["collected_on_request"] is False
    assert out["providers_queried"] == []


def test_run_publishes_evidence_backed_relationships() -> None:
    summary = run(enrich_hsip=False, enrich_hmip=False, enrich_mri=False)
    assert summary["ok"] is True
    assert summary["ask_triggered"] is False
    assert summary["providers_queried"] == []
    assert summary["published"] >= 20
    assert summary["rejected"] == 0

    pack = relationships()
    assert pack["n"] >= 20
    assert pack["providers_queried"] == []
    for rel in pack["relationships"]:
        assert rel["evidence"]
        assert rel["historical_observations"] >= 1
        assert rel["confidence_pct"] >= 60
        assert rel["providers_queried"] == []
        assert rel["inferred_without_evidence"] is False
        assert rel["average_lag"]
        assert rel["version"] >= 1


def test_repo_banking_and_sector_chains() -> None:
    run(enrich_hsip=False, enrich_hmip=False, enrich_mri=False)
    banking = for_sector("Banking")
    assert banking["n"] >= 2
    assert banking["collected_on_request"] is False
    sources = {r["source"] for r in banking["relationships"]}
    targets = {r["target"] for r in banking["relationships"]}
    assert "Repo Rate" in sources or "Banking" in sources
    assert "Real Estate" in targets or "NBFC" in targets or "NIFTY" in targets

    bank_rel = next(
        r
        for r in banking["relationships"]
        if r["source"] == "Repo Rate" or r["target"] == "Real Estate"
    )
    assert bank_rel["confidence_pct"] >= 80
    assert bank_rel["evidence_strength"] in {"High", "Medium"}


def test_company_and_search_surfaces() -> None:
    run(enrich_hsip=False, enrich_hmip=False, enrich_mri=False)
    infy = for_company("INFY")
    assert infy["n"] >= 1
    assert any(r["source"] == "IT Services" or r["target"] == "INFY" for r in infy["relationships"])

    hits = search(q="credit", limit=50)
    assert hits["n"] >= 1
    assert hits["collected_on_request"] is False

    kind_hits = search(kind="sector_to_sector", limit=50)
    assert kind_hits["n"] >= 3


def test_graph_and_transmission_paths() -> None:
    run(enrich_hsip=False, enrich_hmip=False, enrich_mri=False)
    g = graph()
    assert g["n_nodes"] >= 12
    assert g["n_edges"] >= 20
    assert g["providers_queried"] == []
    assert g["transmission_paths"]
    blob = str(g["transmission_paths"]).lower()
    assert "banking" in blob or "real estate" in blob or "repo" in blob

    g2 = graph(start="Banking", end="Cement")
    assert "paths_from" in g2
    assert isinstance(g2["paths_from"], list)


def test_no_evidence_rejected() -> None:
    from sector_relationship_intelligence.schema import SectorRelationship
    from sector_relationship_intelligence.validation import validate_relationship

    bad = SectorRelationship(
        source="X",
        target="Y",
        relationship="Guess",
        kind="sector_to_sector",
        evidence=[],
        historical_observations=0,
    )
    errors = validate_relationship(bad)
    assert "evidence_required" in errors
    assert "historical_observations_must_be_positive" in errors


def test_mission_control_and_traces() -> None:
    run(enrich_hsip=False, enrich_hmip=False, enrich_mri=False)
    for_sector("IT Services")
    board = dashboard()
    assert board["board"] == "Sector Relationship Intelligence"
    assert board["principles"]["evidence_backed_only"] is True
    assert board["total_relationships"] >= 20
    assert board["active_relationships"] >= 1
    assert board["confidence_distribution"]
    assert board["recently_validated_relationships"]
    assert "validation_failures" in board
    names = {t["name"] for t in board["retrieval_performance"]["traces"]}
    all_names = {t["name"] for t in traces.recent(200)}
    assert "sector_relationship_discovery" in all_names
    assert "sector_relationship_validation" in all_names
    assert "sector_relationship_graph" in all_names
    assert "sector_relationship_refresh" in all_names
    assert "sector_relationship_retrieval" in names or "sector_relationship_retrieval" in all_names
