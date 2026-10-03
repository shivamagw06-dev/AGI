"""Phase-1 Ask pipeline observability — request_id, stages, debug payload."""

from __future__ import annotations

from app.ui.ask_observability_store import (
    get_request_debug,
    record_partial_trace,
    reset_for_tests,
)
from app.ui.ask_pipeline_trace import (
    STAGE_ENGINE_RECEIVED,
    STAGE_LLM_STARTED,
    AskPipelineTrace,
    new_request_id,
    normalize_request_id,
    sources_from_degradation,
)


def setup_function() -> None:
    reset_for_tests()


def test_new_request_id_format():
    rid = new_request_id()
    assert rid.startswith("ask_")
    day, hexpart = rid.split("_", 2)[1], rid.split("_", 2)[2]
    assert day.isdigit() and len(day) == 8
    assert len(hexpart) >= 6


def test_normalize_legacy_ask_id():
    assert normalize_request_id("ASK-20260801-4F9D8C12") == "ask_20260801_4f9d8c12"
    assert normalize_request_id("ask_20260801_ab12cd") == "ask_20260801_ab12cd"
    assert normalize_request_id("").startswith("ask_")


def test_pipeline_stages_and_debug_payload():
    t = AskPipelineTrace(request_id="ask_20260801_test01", question="Meta AI capex")
    t.mark(STAGE_ENGINE_RECEIVED)
    t.set_intent("Company Research", confidence=0.97, latency_ms=8)
    t.set_entities(
        [{"name": "META", "ticker": "META", "confidence": 0.98}],
        confidence=0.98,
        aliases_matched=["META"],
        latency_ms=5,
    )
    t.set_source("krig", searched=True, latency_ms=18, returned=24, selected=5)
    t.set_source("kip", searched=True, latency_ms=12, returned=6, selected=2)
    t.set_source("valuation", searched=True, latency_ms=9, returned=3, selected=1)
    t.mark("RETRIEVAL_COMPLETED", status="ok", duration_ms=210)
    t.set_evidence(
        retrieved=37,
        used=8,
        top_ids=["ev1", "ev2"],
        sources=["Knowledge Factory", "KIP", "Valuation"],
        latency_ms=18,
    )
    t.set_prompt(
        prompt_chars=18400,
        estimated_tokens=3900,
        evidence_count=9,
        system_prompt_version="ask-orchestration-trace-2",
        playbook="company_research",
    )
    t.mark(STAGE_LLM_STARTED)
    t.set_llm(
        model="gpt-test",
        prompt_tokens=3900,
        completion_tokens=684,
        latency_ms=1742,
        finish_reason="stop",
    )
    t.complete(status="success")

    debug = t.to_debug_payload()
    assert debug["request_id"] == "ask_20260801_test01"
    assert debug["intent"] == "Company Research"
    assert debug["intent_confidence"] == 0.97
    assert debug["entities"][0]["name"] == "META"
    assert len(debug["sources"]) >= 3
    assert debug["evidence_count"] == 37
    assert debug["prompt_tokens"] == 3900
    assert debug["completion_tokens"] == 684
    assert debug["llm_latency_ms"] == 1742
    assert debug["fallback_used"] is False
    assert debug["status"] == "success"
    assert debug["total_latency_ms"] >= 0
    stages = {e["stage"] for e in debug["events"]}
    assert "ENGINE_RECEIVED" in stages
    assert "INTENT_CLASSIFIED" in stages
    assert "ENTITY_EXTRACTED" in stages
    assert "EVIDENCE_FUSED" in stages
    assert "PROMPT_BUILT" in stages
    assert "LLM_COMPLETED" in stages
    assert "RESPONSE_SENT" in stages

    stored = get_request_debug("ask_20260801_test01")
    assert stored is not None
    assert stored["intent"] == "Company Research"
    # Legacy alias lookup
    assert get_request_debug("ASK-20260801-TEST01") is not None or get_request_debug(
        "ask_20260801_test01"
    )


def test_no_entity_found_never_silent():
    t = AskPipelineTrace(request_id="ask_20260801_noent", question="macro outlook")
    t.set_entities([], none_found=True)
    assert t.entity_note == "No entity found"
    assert t.events[-1]["status"] == "no_entity"


def test_fallback_reason_recorded():
    t = AskPipelineTrace(request_id="ask_20260801_fb", question="x")
    t.set_fallback("timeout", detail={"threshold_ms": 120000})
    t.complete(status="fallback")
    debug = get_request_debug("ask_20260801_fb")
    assert debug["fallback_used"] is True
    assert debug["fallback_reason"] == "timeout"


def test_unknown_intent_logs_why():
    t = AskPipelineTrace(request_id="ask_20260801_unk", question="???")
    t.set_intent("Unknown", confidence=0.0, why_unknown="no research_type")
    assert t.intent_why_unknown == "no research_type"
    assert t.events[-1]["detail"]["why_unknown"] == "no research_type"


def test_sources_from_degradation_always_emits_canonical():
    rows = sources_from_degradation({"krig": "ok", "multi_source": "empty"})
    names = {r["name"] for r in rows}
    assert "Knowledge Factory" in names
    assert "KIP" in names
    assert "Academy" in names
    assert "Private Markets" in names
    assert "Valuation" in names
    assert "Nifty Scores" in names
    assert "Live Filings" in names
    assert "Live Market" in names
    kf = next(r for r in rows if r["name"] == "Knowledge Factory")
    assert kf["searched"] is True


def test_partial_trace_alias_lookup():
    record_partial_trace(
        {
            "ask_trace_id": "ask_20260801_part01",
            "request_id": "ask_20260801_part01",
            "last_completed_stage": "retrieval",
            "elapsed_ms": 400,
            "entity": {"detected": "INFY"},
            "evidence": {"retrieved": 3},
        }
    )
    from app.ui.ask_observability_store import get_partial_trace

    got = get_partial_trace("ask_20260801_part01")
    assert got is not None
    assert got["last_completed_stage"] == "retrieval"
    # Legacy form should also resolve via alias keys
    legacy = get_partial_trace("ASK-20260801-PART01")
    assert legacy is not None
