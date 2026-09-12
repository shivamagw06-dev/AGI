"""Ask orchestration observability — funnel, latency, entity confidence."""

from __future__ import annotations

from app.ui.ask_orchestration_trace import (
    StageTimer,
    build_funnel,
    count_referenced,
    count_retrieved,
    entity_confidence_block,
    executive_attribution,
    finalize_orchestration,
    format_trace_summary,
)


def test_stage_timer_records_ms():
    t = StageTimer()
    t.mark("entity_resolution")
    t.mark("retrieval")
    t.mark("reasoning")
    d = t.as_dict()
    assert "entity_resolution" in d
    assert "retrieval" in d
    assert d["total"] >= 0


def test_funnel_and_utilization():
    f = build_funnel(retrieved=20, ranked=6, passed=4, referenced=3)
    assert f["retrieved"] == 20
    assert f["ranked"] == 6
    assert f["passed_to_ice"] == 4
    assert f["referenced"] == 3
    assert f["utilization"] == 0.75
    assert f["zero_stage"] is None
    empty = build_funnel(retrieved=0, ranked=0, passed=0, referenced=0)
    assert empty["zero_stage"] == "retrieved"


def test_count_retrieved_from_packs():
    n = count_retrieved(
        kf_hits=[{"k": 1}, {"k": 2}],
        finance_retrieval={"hits": [{"symbol": "META"}]},
        multi_source={"evidence_count": 5},
        articles=[{"t": "a"}],
    )
    assert n >= 2 + 1 + 5 + 1


def test_entity_confidence_alias_meta():
    block = entity_confidence_block(
        detected_ticker="META",
        ere_body={"entity": "Artificial Intelligence", "entity_type": "Theme", "confidence": 0.94},
        ticker_source="alias_override",
        question="What did Meta say about AI capex?",
        alias_hit="META",
    )
    assert block["detected"] == "META"
    assert block["confidence"] >= 0.98
    assert "META" in block["aliases_matched"]


def test_entity_rejects_summarize_confidence_zero_without_ticker():
    block = entity_confidence_block(
        detected_ticker=None,
        ere_body={"needs_clarification": True, "research_blocked": True, "confidence": 0},
        ticker_source=None,
        question="Summarize India's mid-2026 equity outlook.",
    )
    assert block["detected"] is None
    assert block["needs_clarification"] is True
    assert block["confidence"] == 0.0


def test_referenced_and_attribution():
    evidence = [
        {"title": "Meta Q2 earnings AI capex", "source": "CMS"},
        {"title": "Unrelated steel note", "source": "CMS"},
    ]
    exec_text = "Meta guided higher AI capex in Q2. The steel note is unrelated noise."
    n = count_referenced(evidence_used=evidence, why=["Evidence: Meta Q2 earnings"], executive=exec_text)
    assert n >= 1
    rows = executive_attribution(executive=exec_text, evidence_used=evidence)
    assert rows
    assert any(r.get("grounded") for r in rows)


def test_finalize_trace_summary():
    timer = StageTimer()
    timer.mark("entity_resolution")
    timer.mark("retrieval")
    orch = finalize_orchestration(
        {"ticker_source": "alias", "executive_source": "answer_construction_over_ice_meta"},
        timer=timer,
        question="What did Meta say in Q2 2026 about AI capex?",
        detected_ticker="META",
        ere_body={"entity": "Meta Platforms", "entity_type": "Company", "confidence": 0.99},
        alias_hit="META",
        kf_hits=[{"title": "a"}, {"title": "b"}],
        evidence_used=[{"title": "Meta Q2 AI capex", "source": "CMS"}],
        supporting_research=[{"title": "Meta 10-Q", "source": "filing"}],
        support_ev=[{"title": "Meta Q2 AI capex"}],
        why=["Evidence: Meta Q2 AI capex guidance"],
        executive="Meta increased AI capex guidance in Q2 per the earnings release.",
        intent="earnings_analysis",
    )
    assert orch["funnel"]["retrieved"] >= 2
    assert orch["funnel"]["ranked"] >= 1
    assert orch["evidence"]["efficiency"] is not None
    assert orch["evidence"]["precision"] is not None
    assert orch["ask_trace_id"].startswith("ask_")
    assert orch["entity"]["detected"] == "META"
    assert orch["entity"]["name"]
    assert "latency" in orch and "entity_ms" in orch["latency"]
    assert "latency_ms" in orch
    assert "Entity:" in orch["trace_summary"]
    assert "Retrieved:" in orch["trace_summary"]
    assert "Trace:" in orch["trace_summary"]
    summary = format_trace_summary(orch)
    assert "META" in summary or "Meta" in summary
