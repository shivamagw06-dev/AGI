"""Ask observability ring buffer + Mission Control KPI facade."""

from __future__ import annotations

from app.ui.ask_observability_store import kpi_dashboard, record_trace, reset_for_tests
from app.ui.ask_orchestration_trace import (
    StageTimer,
    build_funnel,
    finalize_orchestration,
    new_ask_trace_id,
)
from mission_control.production import ask_observability


def setup_function() -> None:
    reset_for_tests()


def test_trace_id_format():
    tid = new_ask_trace_id()
    assert tid.startswith("ask_")
    assert len(tid) >= 16
    parts = tid.split("_")
    assert len(parts) >= 3
    assert parts[1].isdigit()


def test_funnel_efficiency_and_precision():
    f = build_funnel(retrieved=18, ranked=7, passed=5, referenced=4)
    assert f["utilization"] == 0.8
    assert f["efficiency"] == round(4 / 18, 3)
    assert f["precision"] == round(4 / 7, 3)
    assert f["passed"] == 5


def test_finalize_persists_and_mission_control_reads():
    timer = StageTimer()
    timer.mark("entity_resolution")
    timer.mark("retrieval")
    timer.mark("ranking")
    timer.mark("reasoning")
    timer.mark("response_assembly")
    timer.mark("serialization")
    orch = finalize_orchestration(
        {"ticker_source": "alias", "ticker_rejects": [{"raw": "SUMMARIZE", "source": "final"}]},
        timer=timer,
        question="What did Meta say about AI?",
        detected_ticker="META",
        ere_body={"entity": "Meta Platforms", "entity_type": "Company", "confidence": 0.99},
        alias_hit="META",
        kf_hits=[{"t": 1}] * 10,
        evidence_used=[{"title": "Meta Q2 AI capex", "source": "CMS"}] * 4,
        supporting_research=[{"title": "Meta call", "source": "transcript"}],
        support_ev=[{"title": "Meta Q2 AI capex"}],
        why=["Evidence: Meta Q2 AI capex"],
        executive="Meta raised AI capex in Q2. Guidance came from the earnings release.",
        intent="earnings_analysis",
        persist=True,
    )
    assert orch["ask_trace_id"].startswith("ask_")
    assert orch["evidence"]["efficiency"] is not None
    assert orch["evidence"]["precision"] is not None
    assert "entity_ms" in orch["latency"]
    assert "SUMMARIZE" in (orch["entity"].get("rejected_candidates") or [])

    dash = kpi_dashboard()
    assert dash["sample_size"] >= 1
    assert dash["kpis"]["entity_success_rate"] is not None

    mc = ask_observability(limit=5)
    assert mc["ok"] is True
    assert mc["diagnostics_visibility"] == "internal"
    assert mc["sample_size"] >= 1
    assert mc["recent_traces"]


def test_record_trace_direct():
    record_trace(
        {
            "ask_trace_id": "ASK-TEST-1",
            "fallback": False,
            "engine_reached": True,
            "entity": {"detected": "RELIANCE", "confidence": 0.95},
            "evidence": {
                "retrieved": 8,
                "ranked": 4,
                "passed": 3,
                "referenced": 2,
                "utilization": 0.667,
                "efficiency": 0.25,
                "precision": 0.5,
            },
            "latency": {"total_ms": 1200, "reasoning_ms": 900},
            "executive_attribution": [{"grounded": True}, {"grounded": False}],
        }
    )
    dash = kpi_dashboard()
    assert dash["sample_size"] >= 1
    assert dash["funnel"]["avg_retrieved"] is not None
