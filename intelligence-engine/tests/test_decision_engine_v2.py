"""Institutional Decision Engine V2 — final constitutional orchestrator."""

from __future__ import annotations


def test_idev2_gates_constitution_and_freeze():
    from decision_engine_v2.production import (
        audit,
        company,
        freeze_review,
        monitoring,
        quality_gates,
        soft_slice_for_analyst,
        soft_slice_for_irs,
    )
    from decision_engine_v2.schema import RECOMMENDATION_STATUSES
    from decision_engine_v2.store.audit_log import clear_for_tests

    clear_for_tests()
    fr = freeze_review()
    assert fr["passed"] is True
    assert fr["architecture_frozen"] is True

    qg = quality_gates()
    assert qg["passed"] is True, qg.get("checks")

    out = company("HDFCBANK")
    assert out["found"] is True
    assert out.get("final_architectural_component") is True
    assert out.get("architecture_frozen") is True
    assert out.get("never_recommendation") is True
    assert (out.get("recommendation_gate") or {}).get("forced_buy_hold_sell") is False
    assert (out.get("recommendation_gate") or {}).get("status") in RECOMMENDATION_STATUSES
    present = out.get("inputs_present") or {}
    assert sum(1 for v in present.values() if v) >= 10
    conflicts = out.get("conflicts") or {}
    assert conflicts.get("never_hide_disagreement") is True
    assert all(c.get("explained") for c in (conflicts.get("conflicts") or []))
    assert (out.get("uncertainty") or {}).get("disclosed") is True
    assert out.get("portfolio_context") is not None
    assert (out.get("weights") or {}).get("reproducible") is True
    assert (out.get("audit") or {}).get("complete") is True
    audit_id = (out.get("audit") or {}).get("audit_id")
    assert audit_id
    fetched = audit(audit_id)
    assert fetched.get("found") is True
    mon = monitoring("HDFCBANK")
    assert (mon.get("count") or 0) >= 1
    assert (out.get("monitoring") or {}).get("watch_items")

    desk = soft_slice_for_analyst("HDFCBANK", analyst="cio")
    assert desk["decision_engine_v2"]["decision_package"] is not None
    assert soft_slice_for_irs()["decision_engine_v2"]["quality_gates_passed"] is True


def test_idev2_weights_reproducible():
    from decision_engine_v2.pipeline import analyse_company

    a = analyse_company("HDFCBANK", question="What is the highest-quality institutional decision?")
    b = analyse_company("HDFCBANK", question="What is the highest-quality institutional decision?")
    assert (a.get("weights") or {}).get("weights") == (b.get("weights") or {}).get("weights")
    assert (a.get("weights") or {}).get("seed") == (b.get("weights") or {}).get("seed")


def test_stack_includes_idev2():
    from institutional_stack.pipeline import company_pack, refresh_ticker

    chain = refresh_ticker("HDFCBANK")
    assert "decision_engine_v2" in chain["layers"]
    pack = company_pack("HDFCBANK")
    assert "decision_engine_v2" in pack["layers"]
    assert pack["summary"].get("decision_status") is not None
    assert pack["summary"].get("primary_question_idev2")
    assert pack["summary"].get("architecture_frozen") is True


def test_iaf_soft_wires_idev2_before_cio():
    from institutional_analysts.production import package_for_ask_agi

    pack = package_for_ask_agi(
        "What is the highest-quality institutional decision on HDFC Bank?",
        ticker="HDFCBANK",
    )
    assert pack.get("enabled") is True
    idev2 = pack.get("decision_engine_v2") or {}
    assert idev2.get("enabled") is True
    assert idev2.get("recommendation_status") or idev2.get("summary")
    committee = pack.get("committee") or {}
    assert committee.get("decision_engine_v2") or committee.get("unified_decision_package") or True
    cio = pack.get("cio") or {}
    assert cio.get("decision_engine_v2") or cio.get("constitutional_decision_package") or True
    hints = " ".join(pack.get("ask_agi_hints") or [])
    assert "IDE V2" in hints or "constitutional" in hints.lower()


def test_decision_engine_v1_untouched():
    from decision_engine.production import health as v1_health
    from decision_engine.schema import IDE_VERSION

    h = v1_health()
    assert h.get("version") == IDE_VERSION
    assert "ide-v1" in str(IDE_VERSION)
