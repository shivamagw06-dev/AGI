"""Accounting Intelligence Engine V1 — trust the statements?"""

from __future__ import annotations


def test_aci_hdfc_quality_gates_and_behaviour():
    from accounting_intelligence.production import (
        analyse,
        quality_gates,
        soft_slice_for_analyst,
        soft_slice_for_irs,
    )

    out = analyse("HDFCBANK")
    assert out["found"] is True
    assert out["primary_question"].startswith("Can the financial")
    assert (out.get("earnings") or {}).get("earnings_quality") is not None
    assert (out.get("cash") or {}).get("cash_quality") is not None
    assert (out.get("working_capital") or {}).get("working_capital") is not None
    assert (out.get("forensic") or {}).get("beneish", {}).get("beneish_m") is not None
    assert (out.get("forensic") or {}).get("piotroski", {}).get("piotroski_f") is not None
    assert (out.get("behaviour") or {}).get("primary")
    assert (out.get("evidence") or {}).get("count", 0) >= 1
    assert (out.get("report") or {}).get("accounting_quality_score") is not None

    qg = quality_gates()
    assert qg["passed"] is True

    fa = soft_slice_for_analyst("HDFCBANK", analyst="financial")
    assert fa["accounting_intelligence"]["desk"]["earnings"]
    ba = soft_slice_for_analyst("HDFCBANK", analyst="business")
    assert "summary" in (ba["accounting_intelligence"].get("desk") or {})
    assert soft_slice_for_irs()["accounting_intelligence"]["quality_gates_passed"] is True


def test_aci_forensic_models_nestle():
    from accounting_intelligence.production import analyse

    out = analyse("NESTLEIND")
    assert out["found"] is True
    altman = (out.get("forensic") or {}).get("altman") or {}
    assert altman.get("altman_z") is not None
    assert altman.get("zone") in {"safe", "grey", "distress"}


def test_stack_includes_aci():
    from institutional_stack.pipeline import company_pack, refresh_ticker

    chain = refresh_ticker("HDFCBANK")
    assert "accounting_intelligence" in chain["layers"]
    pack = company_pack("HDFCBANK")
    assert pack["summary"]["accounting_behaviour"]
    assert pack["summary"]["accounting_quality_score"] is not None
    assert "accounting_intelligence" in pack["layers"]


def test_fa_knowledge_resolves_aci():
    from institutional_analysts.financial.brain.knowledge.catalog import knowledge_pack

    pack = knowledge_pack("HDFCBANK")
    assert pack["accounting_intelligence"]["enabled"] is True
    assert pack["accounting_intelligence"].get("behaviour") or pack["accounting_intelligence"].get(
        "confidence"
    ) is not None
