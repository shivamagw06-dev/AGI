"""P3.2 Investment Knowledge Graph — unit tests."""

from __future__ import annotations

from investment_knowledge_graph.build import build_company_graph, query_macro_chain, query_theme
from investment_knowledge_graph.enrich import merge_graph_into_dossier
from investment_knowledge_graph.production import health
from investment_knowledge_graph.retrieve import retrieve_composite
from investment_knowledge_graph.schema import EDGE_TYPES, ENGINE_CODE, NODE_TYPES, VERSION


def _memory_stub() -> dict:
    return {
        "ok": True,
        "entity": "TCS",
        "sector_history": {"sector_key": "it_services", "kpi_keys": ["Utilisation"]},
        "ownership_history": {
            "latest": {
                "promoter": 72.0,
                "fii": 51.0,
                "dii": 12.0,
                "mutual_funds": 8.6,
                "insurance": 4.5,
            }
        },
        "event_timeline": {
            "n": 2,
            "events": [
                {"date": "2026-07-18", "title": "Q1 Results", "type": "results"},
                {"date": "2026-07-24", "title": "Management raised EBITDA guidance", "type": "guidance"},
            ],
        },
    }


def test_health_catalog():
    h = health()
    assert h["engine"] == ENGINE_CODE
    assert h["version"] == VERSION
    assert h["modifies_decision_engine"] is False
    assert h["decision_engine_consumes_cid_only"] is True
    assert "Company" in h["node_types"]
    assert "COMPETES_WITH" in h["edge_types"]
    assert set(NODE_TYPES) == set(h["node_types"])
    assert set(EDGE_TYPES) == set(h["edge_types"])


def test_build_company_graph_peers_and_themes():
    g = build_company_graph("TCS", memory=_memory_stub())
    assert g["entity"] == "TCS"
    assert g["n_nodes"] >= 5
    assert g["n_edges"] >= 3
    rels = {e["rel"] for e in g["edges"]}
    assert "COMPETES_WITH" in rels or "BELONGS_TO" in rels
    assert "OWNS" in rels
    assert "EXPOSED_TO" in rels  # USD soft for IT
    assert "AI" in (g.get("themes") or []) or any(
        n.get("type") == "Theme" for n in g.get("nodes") or []
    )


def test_theme_and_macro_queries():
    ai = query_theme("AI")
    assert ai["found"] is True
    assert "TCS" in ai["members"]
    macro = query_macro_chain("repo_to_banks")
    assert macro["n"] == 1
    assert "RBI Repo" in macro["chains"][0]["narrative"]


def test_retrieve_composite_shape(monkeypatch):
    from investment_knowledge_graph import retrieve as rmod

    mem = _memory_stub()
    mem["memory_version"] = 2
    mem["coverage"] = {"coverage_pct": 80}
    mem["memory_delta"] = {"status": "UNCHANGED", "summary": "noop"}

    monkeypatch.setattr(
        "knowledge_delta_engine.production.compile_incremental",
        lambda entity, **kwargs: mem,
    )
    pack = retrieve_composite("TCS", include_cid=False, compile_delta=True, persist_delta=False)
    assert pack["retrieval"] == "company_memory+knowledge_graph+latest_delta+cid"
    assert pack["company_memory"]["ok"] is True
    assert pack["knowledge_graph"]["n_nodes"] >= 1
    assert pack["latest_delta"]["status"] == "UNCHANGED"
    assert pack["modifies_decision_engine"] is False
    assert pack["cid"] is None


def test_merge_graph_into_dossier():
    g = build_company_graph("TCS", memory=_memory_stub())
    dossier = merge_graph_into_dossier({"ticker": "TCS", "identity": {}, "evidence": []}, g)
    assert dossier["investment_knowledge_graph"]["ok"] is True
    assert dossier["investment_knowledge_graph"]["n_edges"] == g["n_edges"]
    assert any(e.get("evidence_type") == "investment_knowledge_graph" for e in dossier["evidence"])
