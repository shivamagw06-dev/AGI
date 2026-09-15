"""Sprint 10.3 — Macroeconomic Relationship Intelligence tests."""

from __future__ import annotations

from macroeconomic_relationship_intelligence import traces
from macroeconomic_relationship_intelligence.production import (
    dashboard,
    for_company,
    for_indicator,
    for_sector,
    graph,
    health,
    relationships,
    run,
)
from macroeconomic_relationship_intelligence.schema import NO_MRI_ACTIONS
from macroeconomic_relationship_intelligence.store import reset
from historical_macro_intelligence.production import run as hmip_run
from historical_macro_intelligence.store import reset as hmip_reset


def setup_function() -> None:
    reset()
    traces.clear()
    hmip_reset()


def test_mri_health() -> None:
    h = health()
    assert h["status"] == "ok"
    assert h["programme_short"] == "MRI"
    assert h["ask_triggers_collection"] is False
    assert h["providers_queried_always"] == []
    for item in NO_MRI_ACTIONS:
        assert item in h["does_not"]


def test_read_never_rebuilds() -> None:
    out = relationships()
    assert out["n"] == 0
    assert out["collected_on_request"] is False
    assert out["providers_queried"] == []


def test_run_publishes_evidence_backed_relationships() -> None:
    hmip_run()  # soft enrichment source
    summary = run()
    assert summary["ok"] is True
    assert summary["ask_triggered"] is False
    assert summary["published"] >= 15
    assert summary["rejected"] == 0

    pack = relationships()
    assert pack["n"] >= 15
    assert pack["providers_queried"] == []
    for rel in pack["relationships"]:
        assert rel["evidence"]
        assert rel["historical_observations"] >= 1
        assert rel["confidence_pct"] >= 60
        assert rel["providers_queried"] == []
        assert rel["inferred_without_evidence"] is False
        assert rel["average_lag"] or rel["kind"] == "macro_to_macro"


def test_repo_private_banks_relationship() -> None:
    hmip_run()
    run()
    rows = for_indicator("Repo Rate")
    assert rows["n"] >= 2
    assert rows["collected_on_request"] is False
    targets = {r["target"] for r in rows["relationships"]}
    assert "Private Banks" in targets or "HDFCBANK" in targets
    bank = next(r for r in rows["relationships"] if r["target"] in {"Private Banks", "HDFCBANK"})
    assert bank["confidence_pct"] >= 85
    assert bank["evidence_strength"] in {"High", "Medium"}
    assert "Historical Macro" in bank["supporting_layers"] or bank["evidence"]


def test_company_and_sector_surfaces() -> None:
    hmip_run()
    run()
    infy = for_company("INFY")
    assert infy["n"] >= 1
    assert any(r["source"] in {"USDINR", "Federal Funds Rate"} for r in infy["relationships"])

    fmcg = for_sector("FMCG")
    assert fmcg["n"] >= 1
    assert any(r["source"] == "CPI" for r in fmcg["relationships"])

    it = for_sector("IT Services")
    assert it["n"] >= 1


def test_graph_and_transmission_paths() -> None:
    hmip_run()
    run()
    g = graph()
    assert g["n_nodes"] >= 10
    assert g["n_edges"] >= 15
    assert g["providers_queried"] == []
    assert g["transmission_paths"]
    # Fed → … chain should appear
    blob = str(g["transmission_paths"]).lower()
    assert "federal" in blob or "usdinr" in blob or "nifty" in blob


def test_no_evidence_rejected() -> None:
    from macroeconomic_relationship_intelligence.schema import MacroRelationship
    from macroeconomic_relationship_intelligence.validation import validate_relationship

    bad = MacroRelationship(
        source="X",
        target="Y",
        relationship="Guess",
        kind="macro_to_sector",
        evidence=[],
        historical_observations=0,
    )
    errors = validate_relationship(bad)
    assert "evidence_required" in errors
    assert "historical_observations_must_be_positive" in errors


def test_mission_control_and_traces() -> None:
    hmip_run()
    run()
    for_indicator("CPI")
    board = dashboard()
    assert board["board"] == "Macro Relationship Intelligence"
    assert board["principles"]["evidence_backed_only"] is True
    assert board["total_relationships"] >= 15
    assert board["relationship_confidence_distribution"]
    assert board["recently_validated_relationships"]
    names = {t["name"] for t in board["retrieval_performance"]["traces"]}
    all_names = {t["name"] for t in traces.recent(200)}
    assert "macro_relationship_discovery" in all_names
    assert "macro_relationship_validation" in all_names
    assert "macro_relationship_graph" in all_names
    assert "macro_relationship_retrieval" in names or "macro_relationship_retrieval" in all_names
