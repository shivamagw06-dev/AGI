"""IEP-01 — Institutional Evidence Platform tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from institutional_evidence.schema import (
    IEP_WORKSTREAM_ID,
    PHASE1_TOP20,
    PHASE1_UNIVERSE,
    RESEARCH_READY_THRESHOLD,
)
from institutional_evidence.canonical.statements import map_provider_to_canonical
from institutional_evidence.registry.store import register_documents
from institutional_evidence.validator.pack_validator import (
    ci_gate_failures,
    validate_research_pack_dict,
)
from institutional_evidence.readiness.index import compute_research_readiness
from institutional_evidence.gates import (
    gate_decision_recommendation,
    gate_publishing,
    gate_research_writer,
)
from institutional_evidence.production import get_iep_status, soft_slice_mission_control
from institutional_evidence.flags import iep_flags
from financial_statements_engine.extraction.nse_xbrl import extract_from_earnings_pack


def _sample_earnings_pack():
    return {
        "ok": True,
        "ticker": "RELIANCE",
        "confidence": 0.9,
        "quarter_history": [
            {
                "period": "FY26Q1",
                "period_end": "2025-06-30",
                "revenue": 250000,
                "ebitda": 45000,
                "pat": 18000,
                "eps": 12.5,
                "total_debt": 90000,
                "cash": 40000,
                "capex": 15000,
            },
            {
                "period": "FY25Q4",
                "period_end": "2025-03-31",
                "revenue": 240000,
                "ebitda": 43000,
                "pat": 17000,
                "eps": 11.8,
            },
        ],
        "annual_history": [
            {
                "period": "FY25",
                "period_end": "2025-03-31",
                "revenue": 900000,
                "ebitda": 160000,
                "pat": 65000,
                "eps": 45.0,
            }
        ],
    }


def test_phase1_universe_is_top_20():
    assert len(PHASE1_UNIVERSE) == 20
    assert len(PHASE1_TOP20) == 20
    assert "RELIANCE" in PHASE1_UNIVERSE
    assert IEP_WORKSTREAM_ID == "IEP-01"


def test_fse_extract_accepts_quarter_history():
    extracted = extract_from_earnings_pack(_sample_earnings_pack())
    assert len(extracted["periods"]) >= 3
    assert any(p.get("period_type") == "quarterly" for p in extracted["periods"])
    assert any(p.get("period_type") == "annual" for p in extracted["periods"])


def test_canonical_maps_provider_history():
    canon = map_provider_to_canonical(
        _sample_earnings_pack(),
        company="Reliance Industries",
        ticker="RELIANCE",
        source="earnings_intelligence",
    )
    d = canon.to_dict()
    assert d["period_count"] >= 3
    assert d["published"] is True
    assert d["income_statement"][0]["revenue"] == 250000
    # no provider-specific raw keys leaked at top level
    assert "quarter_history" not in d


def test_registry_requires_hash_and_is_immutable():
    acq = {
        "ticker": "RELIANCE",
        "company": "Reliance Industries",
        "documents": [
            {
                "document_id": "doc_a",
                "document_type": "quarterly_results",
                "source": "nse",
                "hash": "abc123hash",
                "checksum": "abc123hash",
                "published_at": "2025-07-01T00:00:00Z",
                "downloaded_at": "2025-07-02T00:00:00Z",
            },
            {
                "document_id": "doc_no_hash",
                "document_type": "news",
                "source": "news",
                # missing hash — skipped
            },
        ],
    }
    reg = register_documents(acq)
    assert reg["evidence_count"] >= 1
    assert reg["missing_hash_skipped"] >= 1
    eid = reg["items"][0]["evidence_id"]
    # re-register same hash → immutable (count unchanged)
    reg2 = register_documents(acq)
    assert reg2["evidence_count"] == reg["evidence_count"]
    assert any(i["evidence_id"] == eid for i in reg2["items"])


def test_validator_blocks_empty_pack():
    pack = {
        "financials": {"periods": [], "published": False, "zero_periods": True},
        "evidence": {"registry": {"items": []}, "primary_citation_ids": []},
        "company_memory": {"ok": True, "slot_coverage": 0.05},
        "research_readiness": {"score": 10, "research_ready": False},
        "sector": "Energy",
        "decision": {"recommendation": "BUY"},
    }
    v = validate_research_pack_dict(pack)
    assert v["claim_safe"] is False
    assert v["blocked"] is True
    assert any("zero_periods" in f for f in v["failures"])
    gates = ci_gate_failures(pack)
    assert any("zero periods" in g for g in gates)


def test_validator_claim_safe_with_complete_fixture():
    from datetime import datetime, timezone

    fresh_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    canon = map_provider_to_canonical(
        _sample_earnings_pack(),
        company="Reliance Industries",
        ticker="RELIANCE",
        source="earnings_intelligence",
    ).to_dict()
    acq = {
        "ticker": "RELIANCE",
        "company": "Reliance Industries",
        "documents": [
            {
                "document_id": "doc_q",
                "document_type": "quarterly_results",
                "source": "nse",
                "hash": "rel_q_hash_fresh_001",
                "checksum": "rel_q_hash_fresh_001",
                "published_at": fresh_at,
            }
        ],
    }
    reg = register_documents(acq)
    pack = {
        "financials": canon,
        "evidence": {
            "registry": reg,
            "primary_citation_ids": [
                i["evidence_id"] for i in reg["items"] if i.get("research_ready")
            ]
            or [reg["items"][0]["evidence_id"]],
        },
        "company_memory": {"ok": True, "slot_coverage": 0.4},
        "sector": "Energy / Conglomerate",
        "decision": {"recommendation": "MONITOR"},
        "valuation": {"pe": 25},
        "knowledge_graph": {"nodes": 3},
    }
    pack["research_readiness"] = compute_research_readiness(pack)
    v = validate_research_pack_dict(pack)
    assert v["checks"]["financial_statements"] is True
    assert v["claim_safe"] is True


def test_gates_block_writer_decision_publish_when_unsafe(monkeypatch):
    monkeypatch.setenv("AGI_IEP_BLOCK_RESEARCH", "1")
    monkeypatch.setenv("AGI_IEP_BLOCK_RECOMMENDATION", "1")
    monkeypatch.setenv("AGI_IEP_BLOCK_PUBLISH", "1")

    empty = {
        "schema": "InstitutionalResearchPack.v1",
        "ticker": "RELIANCE",
        "claim_safe": False,
        "research_ready": False,
        "validation": {"failures": ["canonical_statements_zero_periods"]},
        "missing_components": ["canonical_financial_statements"],
        "forbidden_invented_fields": ["revenue", "eps"],
        "research_readiness": {"score": 5, "research_ready": False},
    }
    w = gate_research_writer("RELIANCE", pack=empty)
    assert w["allowed"] is False
    assert "Evidence unavailable" in w["message"]

    d = gate_decision_recommendation("RELIANCE", "BUY", pack=empty)
    assert d["allowed"] is False
    assert d["recommendation"] == "NO RECOMMENDATION"

    p = gate_publishing("RELIANCE", pack=empty)
    assert p["allowed"] is False
    assert p["rejected"] is True


def test_status_and_soft_slice():
    st = get_iep_status()
    assert st["ok"] is True
    assert st["workstream_id"] == "IEP-01"
    assert "Data Governance" in st["pipeline"]
    assert "LLM" in st["anti_pipeline"]
    slice_ = soft_slice_mission_control()
    assert slice_["board"] == "Evidence Center"
    assert slice_["phase1_total"] == 20
    flags = iep_flags()
    assert "iep_enabled" in flags
    assert RESEARCH_READY_THRESHOLD == 70.0


def test_readiness_scores_complete_pack_above_threshold():
    canon = map_provider_to_canonical(
        _sample_earnings_pack(),
        company="Reliance Industries",
        ticker="RELIANCE",
        source="earnings_intelligence",
    ).to_dict()
    # pad periods to 4 for full FS score
    while len(canon["periods"]) < 4:
        canon["periods"].append(dict(canon["periods"][0]))
    pack = {
        "financials": canon,
        "evidence": {
            "registry": {
                "items": [
                    {
                        "evidence_id": "ev1",
                        "research_ready": True,
                        "authority_score": 0.95,
                        "freshness_ok": True,
                        "hash": "h1",
                    },
                    {
                        "evidence_id": "ev2",
                        "research_ready": True,
                        "authority_score": 0.9,
                        "freshness_ok": True,
                        "hash": "h2",
                    },
                ]
            }
        },
        "company_memory": {"slot_coverage": 0.5},
        "valuation": {"pe": 22},
        "knowledge_graph": {"ok": True},
        "decision": {"recommendation": "MONITOR"},
    }
    r = compute_research_readiness(pack)
    assert r["score"] >= RESEARCH_READY_THRESHOLD
    assert r["research_ready"] is True
    assert r["status"] == "Research Ready"
