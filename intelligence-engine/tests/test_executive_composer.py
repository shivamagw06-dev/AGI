"""Executive Composer contract — scaffold ban, unknown stop, compare ≥2."""

from __future__ import annotations

from app.ui.executive_composer import (
    alias_tickers_from_question,
    comparison_entity_count,
    compose_executive,
    finalize_executive,
    is_comparison_question,
    is_planning_scaffold,
    requires_resolved_company,
    unknown_entity_executive,
    validate_executive,
)
from app.ui.ticker_guard import looks_like_framework_meta_executive


def test_scaffold_detects_analyse_via_and_committee():
    bad = (
        "Analyse via Financial evidence (5 items) Analyse via Industry evidence "
        "(1 items) Evidence: RELIANCE expectations"
    )
    assert is_planning_scaffold(bad)
    assert looks_like_framework_meta_executive(bad)
    assert is_planning_scaffold(
        "AGIB's view on LT starts here because own LT only when franchise durability "
        "and financial quality justify the entry after macro transmission. "
        "Position sizing should respect the valuation cushion."
    )
    assert not is_planning_scaffold(
        "Reliance earns cash across refining, retail, and Jio digital platforms."
    )


def test_unknown_entity_message():
    text = unknown_entity_executive(
        "Explain XYZ Quantum Robotics Pvt Ltd.", rejected=["LT"]
    )
    assert "couldn't identify" in text.lower() or "could not identify" in text.lower()
    assert "LT" in text
    assert "XYZ" not in text or "invent" in text.lower()


def test_requires_company_for_explain_pvt_ltd_not_macro():
    assert requires_resolved_company("Explain XYZ Quantum Robotics Pvt Ltd.")
    assert requires_resolved_company("What is Reliance Industries' business model?")
    assert not requires_resolved_company("Summarize India's mid-2026 equity outlook.")
    assert not requires_resolved_company("Explain why banks trade on P/B instead of EV/EBITDA.")


def test_requires_company_exempts_recognized_finance_concepts():
    """A bare 'Explain <term>' must not require a company when <term> is a
    real financial_foundations/financial_statement_intelligence concept —
    this was the AFI Acceptance Test v1.0 A7/A10-style routing bug."""
    assert not requires_resolved_company("Explain retained earnings.")
    assert not requires_resolved_company("Explain the accounting equation.")
    assert not requires_resolved_company("Describe trial balance")
    assert not requires_resolved_company("What is EBITDA?")
    # Real companies (and unknown ones shaped like companies) must still hard-stop.
    assert requires_resolved_company("Explain Tata Motors.")
    assert requires_resolved_company("Explain XYZ Quantum Robotics Pvt Ltd.")


def test_comparison_requires_two_aliases():
    assert is_comparison_question("Compare Infosys vs TCS.")
    assert alias_tickers_from_question("Compare Infosys vs TCS.") == ["INFY", "TCS"]
    assert comparison_entity_count("Compare Infosys vs TCS.") >= 2
    assert alias_tickers_from_question("Compare HDFC Bank vs ICICI Bank.") == [
        "HDFCBANK",
        "ICICIBANK",
    ]
    assert comparison_entity_count("Compare HDFC Bank vs ICICI Bank.") >= 2
    assert comparison_entity_count("Compare Infosys.") < 2


def test_compose_replaces_scaffold_with_question_lead():
    out = compose_executive(
        "What is Reliance Industries' business model?",
        detected_ticker="RELIANCE",
        evidence_used=[
            {"title": "Reliance O2C and retail cash engines", "source": "kf"},
            {"title": "Jio subscriber and ARPU note", "source": "cms"},
        ],
        packs={
            "company_analysis": {
                "summary": (
                    "Reliance combines refining & petrochemicals (O2C), retail, "
                    "and digital services (Jio) as linked cash engines."
                )
            }
        },
        candidates=[
            "Analyse via Financial evidence (5 items) Evidence: RELIANCE expectations"
        ],
        why=["This matters because committee vote 7 / 9 → Neutral"],
    )
    assert out["replaced_scaffold"] is True
    assert not is_planning_scaffold(out["executive"])
    assert "analyse via" not in out["executive"].lower()
    assert "reliance" in out["executive"].lower() or "O2C" in out["executive"]
    assert out["executive"].lower().split(".")[0]  # has a sentence
    # why should not be committee boilerplate
    assert all(not is_planning_scaffold(w) for w in out["why"])


def test_compose_keeps_clean_upstream():
    clean = "Infosys trails TCS on scale but invests faster in generative AI deals."
    out = compose_executive(
        "Compare Infosys vs TCS.",
        detected_ticker="INFY",
        candidates=[clean],
        why=["Scale and margins differ across the two franchises."],
    )
    assert out["replaced_scaffold"] is False
    assert out["executive"] == clean


def test_golden_founder_scorer_offline():
    from ask_product_test.golden_founder_5 import GOLDEN_FOUNDER_5, score_golden_answer

    g1, g4, g5 = GOLDEN_FOUNDER_5[0], GOLDEN_FOUNDER_5[3], GOLDEN_FOUNDER_5[4]
    bad = score_golden_answer(
        g1,
        summary="Analyse via Financial evidence (5 items) Evidence: RELIANCE",
        why=["committee vote 7 / 9"],
    )
    assert bad["pass"] is False
    assert "executive_is_planning_scaffold" in bad["failures"]
    assert bad["score"] < 25
    assert bad["hard_fail_flags"].get("framework_scaffold_appears") is True

    good_policy = score_golden_answer(
        g4,
        summary=(
            "AGIB does not issue buy or sell recommendations. HDFC Bank can be monitored "
            "through franchise quality."
        ),
        orch={"executive_source": "recommendation_policy", "short_circuit": "recommendation_policy"},
    )
    assert good_policy["pass"] is True
    assert good_policy["score"] == 30
    assert not good_policy["hard_fail_flags"]

    good_unknown = score_golden_answer(
        g5,
        summary=(
            "I couldn't identify a verified company for this question, so I won't invent "
            "a research narrative or substitute another firm."
        ),
        orch={"short_circuit": "unknown_entity", "entity_hard_stop": True},
    )
    assert good_unknown["pass"] is True
    assert good_unknown["score"] == 30

    swapped = score_golden_answer(
        g5,
        summary="AGIB's view on LT starts here because own LT only when franchise durability",
        why=[],
    )
    assert swapped["pass"] is False
    assert swapped["hard_fail_flags"].get("unknown_entity_hallucinates") is True
    assert swapped["score"] <= 10


def test_rule6_validate_catches_scaffold_and_substitution():
    v1 = validate_executive(
        "What is Reliance's business model?",
        "Analyse via Financial evidence (5 items) Evidence: RELIANCE",
    )
    assert v1["ok"] is False
    assert "banned_scaffold_present" in v1["failures"]

    v2 = validate_executive(
        "Explain XYZ Quantum Robotics Pvt Ltd.",
        "AGIB's view on LT starts here because own LT only when franchise durability",
        rejected=["LT"],
        is_unknown_stop=True,
    )
    assert v2["ok"] is False
    assert any(f.startswith("unrelated_entity_substitution") for f in v2["failures"])
    assert "unknown_entity_did_not_terminate_correctly" in v2["failures"]

    v3 = validate_executive(
        "Compare Infosys vs TCS.",
        "Infosys focuses on consulting-led deals.",
        tickers=["INFY", "TCS"],
        is_comparison=True,
    )
    assert v3["ok"] is False
    assert "comparison_omits_an_entity" in v3["failures"]

    v_ok = validate_executive(
        "What is Reliance's business model?",
        "Reliance earns cash across refining, retail, and Jio digital platforms.",
    )
    assert v_ok["ok"] is True


def test_rule6_finalize_rewrites_once_from_evidence():
    out = finalize_executive(
        "What is Reliance Industries' business model?",
        "Analyse via Financial evidence (5 items) Evidence: RELIANCE expectations",
        why=["committee vote 7 / 9 → Neutral"],
        evidence_used=[{"title": "Reliance O2C and retail cash engines", "source": "kf"}],
        detected_ticker="RELIANCE",
        packs={
            "company_analysis": {
                "summary": "Reliance combines O2C, retail, and Jio digital as linked cash engines."
            }
        },
    )
    assert out["rewritten"] is True
    assert out["validation"]["ok"] is True
    assert not is_planning_scaffold(out["executive"])
    assert "analyse via" not in out["executive"].lower()


def test_rule6_finalize_noop_when_already_clean():
    clean = "Reliance earns cash across refining, retail, and Jio digital platforms."
    out = finalize_executive(
        "What is Reliance's business model?",
        clean,
        why=["Evidence: Reliance O2C profile"],
    )
    assert out["rewritten"] is False
    assert out["executive"] == clean


def test_ice_render_drops_analyse_via():
    from institutional_communication.renderers.engine import render_communication

    ia = {
        "format": "institutional_answer_v1",
        "question": "What is Reliance's business model?",
        "intent_v2": "Explain",
        "question_type": "business_quality",
        "concept_mode": False,
        "sections": {
            "executive_summary": {
                "bullets": ["Intent: Explain", "Entity-bound analysis"],
                "evidence_ids": ["e1"],
            },
            "analysis": {
                "bullets": [
                    "Analyse via Financial evidence (5 items)",
                    "Reliance earns cash across refining, retail, and digital.",
                ],
                "evidence_ids": ["e1"],
            },
            "evidence": {"bullets": ["KF profile"], "evidence_ids": ["e1"]},
            "framework": {"bullets": ["SOTP"], "evidence_ids": []},
            "risks": {"bullets": ["Refining margin volatility"], "evidence_ids": []},
            "conclusion": {"bullets": ["Platform conglomerate"], "evidence_ids": ["e1"]},
            "confidence": {"bullets": ["Band: Medium"], "evidence_ids": []},
            "sources": {"bullets": ["e1"], "evidence_ids": ["e1"]},
        },
        "evidence": {
            "items": [
                {
                    "evidence_id": "e1",
                    "evidence_type": "COMPANY_PROFILE",
                    "title": "Reliance Industries profile",
                    "source": "kf",
                }
            ]
        },
        "frameworks": {
            "framework_ids": ["FW_SOTP"],
            "explanation": {"reason": "Multi-business groups require Sum-of-the-Parts."},
            "confidence": {"band": "Medium", "pct": 60},
        },
        "confidence": {"band": "Medium", "score": 0.6, "pct": 60},
        "playbook": {"playbook_id": "PB_SOTP", "playbook_name": "SOTP", "checklist": {"steps": []}},
        "gaps": {"missing_domains": [], "coverage": 1.0},
        "citations": {"flat": []},
    }
    out = render_communication(ia)
    exec_text = (out.get("executive_summary") or "").lower()
    assert "analyse via" not in exec_text
    assert "intent:" not in exec_text
    assert "reliance" in exec_text or "evidence:" in exec_text
