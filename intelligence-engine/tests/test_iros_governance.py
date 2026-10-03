"""IROS governance layer — lineage, engine confidence, drift, audit, re-eval."""

from __future__ import annotations

from decision_engine.governance.audit import (
    build_audit_record,
    get_audit_record,
    load_previous_snapshot,
    persist_snapshot,
)
from decision_engine.governance.drift import compute_recommendation_delta, compute_thesis_drift
from decision_engine.governance.engine_confidence import build_engine_confidence, rank_critical_missing
from decision_engine.governance.lineage import build_evidence_lineage
from decision_engine.governance.production import package_governance
from decision_engine.governance.reeval_queue import enqueue_reevaluation, list_reeval_queue
from decision_engine.production import package_for_ask_agi
from decision_engine.readiness_gate import evaluate_readiness_gate


def _thin_gate():
    return evaluate_readiness_gate(
        layers={
            "macro": {"score": 72, "status": "partial"},
            "industry": {"score": 70, "status": "complete"},
            "company_quality": {"score": 84, "status": "complete"},
            "financial_quality": {
                "score": 80,
                "company_quality_score": 84,
                "evidence_quality_score": 30,
                "status": "partial",
            },
            "management": {"score": 78, "status": "partial"},
            "valuation": {"score": 58, "status": "partial"},
            "market_expectations": {"score": 55, "status": "partial"},
            "technical": {"score": 40, "status": "incomplete"},
            "risk": {"score": 72, "status": "complete"},
        },
        company_analysis={
            "identity": {
                "company_name": "HDFC Bank",
                "business_model": "Diversified private-sector bank",
                "peers": ["ICICIBANK"],
            },
            "business_quality": {
                "business_quality_score": 84,
                "strengths": ["Strong retail franchise"],
                "weaknesses": ["Margin pressure"],
            },
            "financial_intelligence": {
                "coverage_pct": 30,
                "source": "NSE Filing",
                "period": "Q1 FY27",
                "what_deteriorated": ["nim_guidance"],
                "what_improved": [],
            },
            "valuation_intelligence": {"coverage_pct": 35, "narrative": "Peer band incomplete"},
        },
        name="HDFC Bank",
    )


def test_evidence_lineage_answers_provenance():
    gate = _thin_gate()
    lineage = build_evidence_lineage(
        readiness_gate=gate,
        company_analysis={
            "financial_intelligence": {
                "coverage_pct": 30,
                "source": "NSE Filing",
                "period": "Q1 FY27",
                "ingested_at": "2026-07-29T10:42:00+05:30",
                "collector": "Historical Collector v3",
            },
            "business_quality": {"business_quality_score": 84},
            "valuation_intelligence": {"coverage_pct": 35},
        },
        cid={"shareholding": {"promoter": 26, "as_of": "2025-12-31"}},
        live_evidence={"quote": {"price": 2211.35, "as_of": "2026-07-29T10:00:00Z"}},
    )
    assert lineage["rows"]
    fin = next(r for r in lineage["rows"] if r["dimension"] == "Financial Statements")
    assert fin["source"] == "NSE Filing"
    assert fin["period"] == "Q1 FY27"
    assert fin["collector"]
    assert fin["evidence_hash"]
    assert fin["verified"].startswith("SHA-256:")
    assert fin["confidence_pct"] == 30.0


def test_per_engine_confidence_and_hard_floor():
    gate = _thin_gate()
    eng = build_engine_confidence(
        readiness_gate=gate,
        layers={
            "company_quality": {"score": 84},
            "financial_quality": {"evidence_quality_score": 30},
            "valuation": {"score": 58},
            "macro": {"score": 72},
            "technical": {"score": 40},
        },
        company_analysis={"business_quality": {"business_quality_score": 84}},
    )
    by = eng["by_engine"]
    assert "business" in by
    assert "financial" in by
    assert "valuation" in by
    assert eng["weakest_engine"]
    assert eng["hard_evidence_floor_pct"] <= by["financial"]
    assert eng["weighting_rule"]


def test_critical_missing_ranked_by_impact():
    gate = _thin_gate()
    ranked = rank_critical_missing(readiness_gate=gate)
    assert ranked["items"]
    assert ranked["items"][0]["rank"] == 1
    impacts = [str(i.get("impact")) for i in ranked["items"]]
    # Highest impact items should sort first
    order = {"Very High": 4, "High": 3, "Medium": 2, "Low": 1}
    scores = [order.get(x, 0) for x in impacts]
    assert scores == sorted(scores, reverse=True)
    assert ranked["ingestion_hint"]


def test_thesis_drift_and_recommendation_delta():
    prev = {
        "thesis_stance": "Constructive",
        "investment_thesis_status": "FORMED",
        "recommendation_readiness_pct": 92,
        "institutional_readiness_pct": 90,
        "recorded_at": "2026-06-01T10:00:00Z",
    }
    gate = _thin_gate()
    drift = compute_thesis_drift(
        previous=prev,
        current_gate=gate,
        current_decision={"action": "watch", "investment_thesis_status": "INCONCLUSIVE"},
        company_analysis={
            "financial_intelligence": {
                "what_deteriorated": ["nim_guidance", "valuation_premium"],
            }
        },
    )
    assert drift["previous_thesis"] == "Constructive"
    assert drift["current_thesis"] == "Inconclusive"
    assert drift["thesis_drift"] in {"Moderate", "High"}
    assert any("nim" in r.lower() for r in drift["reasons"])

    delta = compute_recommendation_delta(previous=prev, current_gate=gate)
    assert delta["last_analysis"]["recommendation_readiness_pct"] == 92
    assert delta["today"]["recommendation_readiness_pct"] is not None
    assert delta["delta_pct"] is not None
    assert delta["delta_pct"] < 0
    assert delta["driver"]
    assert delta["reasons"]


def test_audit_persist_and_retrieve(monkeypatch, tmp_path):
    monkeypatch.setenv("KF_HD_STORE_ROOT", str(tmp_path / "hd"))
    gate = _thin_gate()
    eng = build_engine_confidence(readiness_gate=gate, layers={}, company_analysis={})
    lineage = build_evidence_lineage(readiness_gate=gate, company_analysis={})
    critical = rank_critical_missing(readiness_gate=gate)
    drift = compute_thesis_drift(previous=None, current_gate=gate, current_decision={})
    delta = compute_recommendation_delta(previous=None, current_gate=gate)

    record = build_audit_record(
        ticker="HDFCBANK",
        company_name="HDFC Bank",
        query="Should I buy HDFC Bank?",
        readiness_gate=gate,
        decision={"action": "defer", "overall_score": None},
        engine_confidence=eng,
        lineage=lineage,
        thesis_drift=drift,
        recommendation_delta=delta,
        critical_missing=critical,
        price_snapshot=2211.35,
        knowledge_snapshot_at="2026-07-29T10:42:00Z",
    )
    assert record["recommendation_id"].startswith("AGIB-")
    assert "HDFCBANK" in record["recommendation_id"]
    assert record["constitution"] == "v1.4"
    assert record["evidence_hash"]
    assert record["price_snapshot"] == 2211.35
    assert record["reproducible"] is True

    fetched = get_audit_record(record["recommendation_id"])
    assert fetched is not None
    assert fetched["recommendation_id"] == record["recommendation_id"]

    snap = load_previous_snapshot("HDFCBANK")
    assert snap is not None
    assert snap["recommendation_id"] == record["recommendation_id"]


def test_reeval_queue_on_gate_fail(monkeypatch, tmp_path):
    monkeypatch.setenv("KF_HD_STORE_ROOT", str(tmp_path / "hd"))
    gate = _thin_gate()
    critical = rank_critical_missing(readiness_gate=gate)
    job = enqueue_reevaluation(
        ticker="HDFCBANK",
        company_name="HDFC Bank",
        readiness_gate=gate,
        critical_missing=critical,
        recommendation_id="AGIB-TEST-001",
    )
    assert job["status"] == "queued"
    assert job["self_healing"] is True
    assert job["queued_actions"]
    assert any(a["action"] == "rerun_decision_engine" for a in job["queued_actions"])
    q = list_reeval_queue(limit=10)
    assert q["count"] >= 1
    assert q["items"][0]["ticker"] == "HDFCBANK"


def test_package_governance_full_bundle(monkeypatch, tmp_path):
    monkeypatch.setenv("KF_HD_STORE_ROOT", str(tmp_path / "hd"))
    # Seed previous constructive analysis so drift/delta are meaningful
    persist_snapshot(
        "HDFCBANK",
        {
            "thesis_stance": "Constructive",
            "investment_thesis_status": "FORMED",
            "recommendation_readiness_pct": 92,
            "institutional_readiness_pct": 90,
            "recorded_at": "2026-06-01T10:00:00Z",
        },
    )
    gate = _thin_gate()
    gov = package_governance(
        query="Should I buy HDFC Bank?",
        ticker="HDFCBANK",
        company_name="HDFC Bank",
        readiness_gate=gate,
        decision={"action": "watch", "investment_thesis_status": "INCONCLUSIVE"},
        layers={"company_quality": {"score": 84}, "financial_quality": {"evidence_quality_score": 30}},
        company_analysis={
            "financial_intelligence": {
                "coverage_pct": 30,
                "source": "NSE Filing",
                "period": "Q1 FY27",
                "what_deteriorated": ["nim_guidance"],
            },
            "business_quality": {"business_quality_score": 84},
        },
        live_evidence={"quote": {"price": 2211.35}},
        persist=True,
    )
    assert gov["enabled"] is True
    assert gov["version"].startswith("iros-governance")
    assert gov["layers"]["audit"]
    assert gov["evidence_lineage"]["rows"]
    assert gov["engine_confidence"]["engines"]
    assert gov["critical_missing_evidence"]["items"]
    assert gov["thesis_drift"]["previous_thesis"] == "Constructive"
    assert gov["recommendation_delta"]["last_analysis"]["recommendation_readiness_pct"] == 92
    assert gov["audit"]["recommendation_id"].startswith("AGIB-")
    assert gov["reevaluation"]["queued_actions"]


def test_ide_package_attaches_governance(monkeypatch, tmp_path):
    monkeypatch.setenv("KF_HD_STORE_ROOT", str(tmp_path / "hd"))
    out = package_for_ask_agi(
        "Should I buy HDFC Bank?",
        ticker="HDFCBANK",
        company_analysis={
            "ticker": "HDFCBANK",
            "identity": {"company_name": "HDFC Bank", "peers": ["ICICIBANK"]},
            "business_quality": {"business_quality_score": 82, "strengths": ["Franchise"]},
            "financial_intelligence": {"coverage_pct": 28, "narrative": "Thin pack", "source": "NSE Filing"},
        },
        gate_blocked=True,
        force=True,
    )
    assert out.get("governance", {}).get("enabled") is True
    assert out["summary"].get("recommendation_id")
    assert out["summary"].get("weakest_engine")
    assert isinstance(out["answer_enrichment"].get("critical_missing"), list)
