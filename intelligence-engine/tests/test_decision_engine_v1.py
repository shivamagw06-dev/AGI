"""AGIB Investment Decision Engine — soft-wire tests."""

from __future__ import annotations

from answer_construction.production import package_for_ask_agi as ac_package
from decision_engine.intent import is_investment_decision_question
from decision_engine.production import health, package_for_ask_agi, quality_gates
from decision_engine.schema import IDE_VERSION, LAYER_ORDER, LAYER_WEIGHTS


def test_health_and_gates():
    h = health()
    assert h["status"] == "ok"
    assert h["version"] == IDE_VERSION
    assert h["never_skip_layer"] is True
    assert h["decision_last"] is True
    g = quality_gates()
    assert g["passed"] is True
    assert g["checks"]["thirteen_layers"] is True
    assert g["checks"]["never_direct_buy_sell_first"] is True


def test_intent_detects_buy_questions():
    assert is_investment_decision_question("Should I buy Eternal?")
    assert is_investment_decision_question("Is HDFC Bank worth investing?")
    assert is_investment_decision_question("Should I accumulate TCS for the long term?")
    assert not is_investment_decision_question("What is GDP growth in India?")


def test_weights_sum_to_100():
    assert sum(LAYER_WEIGHTS.values()) == 100


def test_thirteen_layers_always_present_even_when_sparse():
    out = package_for_ask_agi(
        "Should I buy Eternal?",
        ticker="ETERNAL.NS",
        company_analysis={
            "ticker": "ETERNAL.NS",
            "identity": {
                "company_name": "Eternal",
                "business_model": "Consumer internet platform spanning food delivery and quick commerce.",
            },
            "business_quality": {"business_quality_score": 72, "grade": "B+"},
            "financial_intelligence": {
                "coverage_pct": 35,
                "narrative": "Growth improving; cash conversion still forming.",
                "what_improved": ["growth"],
                "what_deteriorated": [],
            },
            "valuation_intelligence": {
                "current_pe": 48,
                "forward_pe": 42,
                "premium_discount_vs_history_pct": 18,
                "narrative": "Trading at a premium to history versus still-forming earnings quality.",
            },
            "bull_case": ["Quick commerce scales with better unit economics."],
            "bear_case": ["Competitive intensity compresses margins."],
            "risks": ["Competition", "Execution risk", "Valuation compression"],
            "catalysts": ["Next earnings", "New city expansion"],
        },
        sector_intelligence={"sector_name": "Consumer Internet", "coverage_pct": 60},
        live_evidence={"is_investment": True},
        gate_blocked=True,
        force=True,
    )
    assert out["enabled"] is True
    assert out["active"] is True
    layers = out["layers"]
    assert len(layers) == 13
    assert [layer["id"] for layer in layers] == LAYER_ORDER
    assert layers[-1]["id"] == "decision"
    assert out["decision_last"] is True
    assert out["never_skip_layer"] is True
    # Every layer has reasoning — incomplete evidence never deletes a layer
    for layer in layers:
        assert layer.get("reasoning")
        assert layer.get("status") in {"complete", "partial", "incomplete"}
    assert out["summary"]["gate_blocked"] is True
    assert "deferred" in str(out["summary"]["action"]).lower() or "Recommendation deferred" in str(
        out["decision"].get("action")
    )
    # No raw framework names in reasoning strings
    joined = " ".join(str(layer.get("reasoning") or "") for layer in layers)
    assert "CID" not in joined
    assert "IRP" not in joined
    assert "LEO" not in joined
    assert "SIF" not in joined


def test_decision_not_triggered_for_macro_question():
    out = package_for_ask_agi("What is the RBI doing with interest rates?")
    assert out["enabled"] is True
    assert out["active"] is False


def test_answer_construction_never_leads_with_buy_when_ide_active():
    ide = package_for_ask_agi(
        "Should I buy Eternal?",
        ticker="ETERNAL.NS",
        company_analysis={
            "ticker": "ETERNAL.NS",
            "identity": {"company_name": "Eternal", "business_model": "Food delivery and quick commerce."},
            "business_quality": {"business_quality_score": 80},
        },
        gate_blocked=True,
        force=True,
    )
    assert ide.get("summary", {}).get("confidence_breakdown")
    ac = ac_package(
        query="Should I buy Eternal?",
        executive="Buy Eternal now.",
        thesis="Strong franchise.",
        house_label="Constructive",
        bull=["Scale"],
        bear=["Competition"],
        risks=["Competition"],
        catalysts=["Earnings"],
        why=["Quality franchise with growth optionality."],
        intelligence_construction={
            "enabled": True,
            "company_name": "Eternal",
            "executive_brief": "Eternal is a consumer internet platform combining food delivery and quick commerce.",
            "answer_enrichment": {
                "executive_summary": "Eternal is a consumer internet platform combining food delivery and quick commerce.",
            },
        },
        company_analysis={
            "identity": {"company_name": "Eternal", "business_model": "Food delivery and quick commerce."},
        },
        decision_engine=ide,
        reco_gate={"blocked": True},
        leo_gate={"blocked": True},
    )
    assert ac["enabled"] is True
    assert ac["decision_engine_active"] is True
    assert ac["decision_last"] is True
    exec_l = str(ac["executive"]).lower()
    assert "buy eternal now" not in exec_l
    # Lead may be readiness-gated INCONCLUSIVE card or layered framing — never a binary buy tip
    assert (
        "layer" in exec_l
        or "macro" in exec_l
        or "decision stack" in exec_l
        or "inconclusive" in exec_l
        or "insufficient" in exec_l
        or "withheld" in exec_l
    )
    assert ac.get("decision_conclusion")
    reco = ac.get("recommendation_status") or {}
    assert reco.get("investment_thesis_status") == "INCONCLUSIVE" or reco.get("blocked") is True
    assert reco.get("not_a_negative_view") is True or reco.get("blocked") is True
