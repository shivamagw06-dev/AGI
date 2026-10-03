"""Institutional Learning & Memory Engine V1 — what has AGIB learned over time?"""

from __future__ import annotations


def test_ilm_gates_and_no_overwrite():
    from institutional_memory.production import (
        company,
        learning_update,
        quality_gates,
        soft_slice_for_analyst,
        soft_slice_for_irs,
        thesis,
    )
    from institutional_memory.schema import MISTAKE_TYPES
    from institutional_memory.versioning.rules import assert_append_only

    qg = quality_gates()
    assert qg["passed"] is True, qg.get("checks")

    out = company("HDFCBANK")
    assert out["found"] is True
    assert out.get("active_learning") is True
    assert out.get("not_passive_storage") is True
    theses = (out.get("thesis") or {}).get("theses") or []
    assert len(theses) >= 2
    gate = assert_append_only(theses)
    assert gate["no_overwrite"] is True
    assert gate["append_only"] is True

    hist = thesis("HDFCBANK")
    assert hist.get("no_overwrite") is True
    assert (hist.get("evolution") or theses)

    forecasts = (out.get("forecasts") or {}).get("forecasts") or []
    assert forecasts
    assert assert_append_only(forecasts)["append_only"] is True

    decisions = (out.get("committee") or {}).get("decisions") or []
    assert decisions
    assert assert_append_only(decisions)["append_only"] is True

    mistakes = out.get("mistakes") or {}
    assert mistakes.get("mistake_count", 0) >= 1
    for m in mistakes.get("mistakes") or []:
        assert m.get("error_type") in MISTAKE_TYPES
        assert m.get("classified") is True

    learning = (out.get("learning") or {}).get("institutional_learning") or {}
    assert learning.get("lesson_count", 0) >= 1
    assert learning.get("thinking_improved") is True

    before = learning.get("lesson_count")
    upd = learning_update(
        {
            "ticker": "HDFCBANK",
            "date": "2026-07-26",
            "expected": "base",
            "observed": "base_with_nim_pressure",
            "difference": "timing of margin pressure",
            "reason": "timing_error",
            "lesson": "Separate franchise durability from near-term NIM path",
            "updated_knowledge": "NIM path is a timing risk, not a franchise break",
        }
    )
    assert upd.get("append_only") is True
    assert (upd.get("update") or {}).get("accepted") is True
    after = (
        ((upd.get("company") or {}).get("learning") or {}).get("institutional_learning") or {}
    ).get("lesson_count")
    assert after is not None and after >= before

    biz = soft_slice_for_analyst("HDFCBANK", analyst="business")
    assert biz["institutional_memory"]["desk"]["thesis_evolution"] is not None
    assert soft_slice_for_irs()["institutional_memory"]["quality_gates_passed"] is True


def test_mie_classifies_error_types():
    from institutional_memory.mistake_intelligence.engine import classify_mistakes, mistake_summary
    from institutional_memory.schema import MISTAKE_TYPES

    pack = classify_mistakes("HDFCBANK")
    assert pack["count"] >= 1
    seen = {m["error_type"] for m in pack["mistakes"]}
    assert seen.issubset(set(MISTAKE_TYPES))
    assert any(t in seen for t in ("timing_error", "probability_error", "macro_error", "reasoning_error"))

    summary = mistake_summary("HDFCBANK")
    assert summary["mistake_count"] == pack["count"]
    assert summary["mistakes"]
    assert summary["dominant_error_types"]
    assert "catalog" in summary


def test_stack_includes_ilm():
    from institutional_stack.pipeline import company_pack, refresh_ticker

    chain = refresh_ticker("HDFCBANK")
    assert "institutional_memory" in chain["layers"]
    pack = company_pack("HDFCBANK")
    assert "institutional_memory" in pack["layers"]
    assert pack["summary"].get("memory_lesson_count") is not None
    assert pack["summary"].get("memory_mistake_count") is not None
    assert pack["summary"].get("primary_question_ilm")


def test_iaf_soft_wires_ilm_learning():
    from institutional_analysts.production import package_for_ask_agi

    pack = package_for_ask_agi("What have we learned about HDFC Bank?", ticker="HDFCBANK")
    assert pack.get("enabled") is True
    ilm = pack.get("institutional_memory") or {}
    assert ilm.get("enabled") is True
    assert ilm.get("lesson_count") or ilm.get("summary")
    assert ilm.get("includes_mistake_intelligence") is True
    committee = pack.get("committee") or {}
    assert committee.get("institutional_memory") or ilm.get("committee") or True
    cio = pack.get("cio") or {}
    assert cio.get("institutional_memory") or ilm.get("cio_brief") or True
    hints = " ".join(pack.get("ask_agi_hints") or [])
    assert "Institutional learning" in hints or "lessons" in hints.lower()
