"""AGIB v3.4 Track C — IFSE acceptance tests."""

from __future__ import annotations

import ast
from pathlib import Path

from framework_selection import IFSE_VERSION, select_frameworks
from framework_selection.production import dashboard, health, registry, select
from framework_selection.registry.frameworks import framework_ids, get_framework

ROOT = Path(__file__).resolve().parents[1]


def _ids(sel: dict) -> set[str]:
    return {str(x) for x in (sel.get("framework_ids") or [])}


def test_ifse_version_and_registry() -> None:
    assert IFSE_VERSION.startswith("framework-selection")
    ids = framework_ids()
    assert "FW_RESIDUAL_INCOME" in ids
    assert "FW_EV_EBITDA" in ids
    assert "FW_SOTP" in ids
    assert "FW_MACRO_TRANSMISSION" in ids
    assert len(ids) >= 30
    assert health()["status"] == "ok"
    assert registry()["n"] >= 30


def test_banks_use_pb_and_residual_income() -> None:
    sel = select_frameworks(
        question="Why is HDFC Bank primarily valued using Price-to-Book and Residual Income?",
        intent_v2="Explain",
        entities=[{"type": "company", "id": "HDFCBANK", "confidence": 0.99}],
    )
    ids = _ids(sel)
    assert "FW_RESIDUAL_INCOME" in ids
    assert "FW_PB" in ids
    assert "FW_EV_EBITDA" not in ids
    assert "FW_EV_EBITDA" in (sel.get("forbidden_rejected") or [])
    assert sel["explanation"]["reason"]
    assert sel["confidence"]["pct"] >= 50


def test_banks_forbid_ev_ebitda_concept() -> None:
    sel = select_frameworks(
        question="Explain why EV/EBITDA is generally inappropriate for banks and insurance companies.",
        intent_v2="Explain",
        concept_mode=True,
    )
    assert sel["sector"] == "banks"
    assert "FW_EV_EBITDA" not in _ids(sel)
    assert "FW_FRAMEWORK_EXPLANATION" in _ids(sel)
    assert "FW_PB" in _ids(sel) or "FW_RESIDUAL_INCOME" in _ids(sel)


def test_it_uses_dcf_and_ev_ebitda() -> None:
    sel = select_frameworks(
        question="Compare Infosys valuation frameworks",
        intent_v2="Compare",
        entities=[{"type": "company", "id": "INFY", "confidence": 0.99}],
    )
    ids = _ids(sel)
    assert "FW_DCF" in ids
    assert "FW_EV_EBITDA" in ids
    assert "FW_PEER_COMPARISON" in ids


def test_conglomerates_use_sotp() -> None:
    sel = select_frameworks(
        question="How should AGIB prepare evidence for Reliance before valuation?",
        intent_v2="CrossDomain",
        entities=[{"type": "company", "id": "RELIANCE", "confidence": 0.99}],
    )
    assert "FW_SOTP" in _ids(sel)
    assert sel["sector"] == "conglomerates"
    assert (sel.get("validation") or {}).get("passed") is True


def test_hospitals_healthcare_metrics() -> None:
    sel = select_frameworks(
        question="Explain why hospitals often require a different valuation framework than pharmaceutical manufacturers.",
        intent_v2="Explain",
        concept_mode=True,
    )
    assert sel["sector"] == "hospitals"
    ids = _ids(sel)
    assert "FW_HEALTHCARE_OPS" in ids
    assert "FW_EV_EBITDA" in ids
    # Not DCF-only
    assert not (ids <= {"FW_DCF"})


def test_airlines_aviation_metrics() -> None:
    sel = select_frameworks(
        question="Analyse Indigo airline operating metrics and valuation",
        intent_v2="Analyse",
        entities=[{"type": "company", "id": "INDIGO", "confidence": 0.99}],
    )
    ids = _ids(sel)
    assert "FW_EV_EBITDAR" in ids
    assert "FW_AVIATION_OPS" in ids
    assert "FW_PB" not in ids or len(ids) > 1


def test_cement_capacity_metrics() -> None:
    sel = select_frameworks(
        question="Why do cement companies often experience valuation expansion before earnings improve?",
        intent_v2="Industry",
        concept_mode=True,
    )
    assert sel["sector"] == "cement"
    ids = _ids(sel)
    assert "FW_CEMENT_CAPACITY" in ids
    assert "FW_EV_EBITDA" in ids or "FW_INDUSTRY_STRUCTURE" in ids


def test_macro_transmission_framework() -> None:
    sel = select_frameworks(
        question="Explain inflation transmission through the economy",
        intent_v2="Macro",
        concept_mode=True,
    )
    assert "FW_MACRO_TRANSMISSION" in _ids(sel)


def test_government_policy_framework() -> None:
    sel = select_frameworks(
        question="The Government doubles import duties on steel. Which sectors benefit?",
        intent_v2="Government",
        concept_mode=True,
    )
    assert "FW_POLICY" in _ids(sel)


def test_historical_replay_preserves_framework() -> None:
    sel = select_frameworks(
        question="Replay Infosys as of 31 March 2020",
        intent_v2="HistoricalReplay",
        entities=[{"type": "company", "id": "INFY", "confidence": 0.99}],
        as_of="2020-03-31",
    )
    assert "FW_HISTORICAL_VALUATION" in _ids(sel)
    assert sel["as_of"] == "2020-03-31"
    # Modern frameworks available in 2020 still present
    assert "FW_DCF" in _ids(sel)


def test_multi_framework_composition_expensive_bank() -> None:
    sel = select_frameworks(
        question="Why is HDFC Bank expensive?",
        intent_v2="Explain",
        entities=[{"type": "company", "id": "HDFCBANK", "confidence": 0.99}],
    )
    ids = _ids(sel)
    assert "FW_RESIDUAL_INCOME" in ids
    assert "FW_ROE" in ids
    assert "FW_HISTORICAL_VALUATION" in ids
    assert sel["multi_framework"] is True
    expl = sel["explanation"]
    assert expl["selected_frameworks"]
    assert expl["confidence"]["pct"] is not None


def test_deterministic() -> None:
    kwargs = dict(
        question="Why do banks trade on P/B?",
        intent_v2="Explain",
        concept_mode=True,
    )
    a = select_frameworks(**kwargs)
    b = select_frameworks(**kwargs)
    assert a["framework_ids"] == b["framework_ids"]
    assert a["sector"] == b["sector"]


def test_ask_pipeline_soft_wire() -> None:
    from ask_pipeline.pipeline import run_complete_ask

    out = run_complete_ask(
        "Explain why EV/EBITDA is generally inappropriate for banks and insurance companies.",
        ticker_hint="INFY",
    )
    fs = out.get("framework_selection") or {}
    assert out.get("framework_selection_version", "").startswith("framework-selection")
    assert "FW_EV_EBITDA" not in set(fs.get("framework_ids") or [])
    assert fs.get("llm_used") is False
    assert out.get("reasoning_changed") is False
    inst = out.get("institutional_answer") or {}
    assert (inst.get("framework_selection") or {}).get("explanation")


def test_answer_assembly_integration() -> None:
    from ask_pipeline.answer_assembly import assemble_answer_plan
    from ask_pipeline.intent_resolution import resolve_intent

    q = "Why do banks trade on P/B?"
    irl = resolve_intent(q)
    plan = assemble_answer_plan(
        question=q,
        intent_v2=irl["intent"],
        intent_resolution=irl,
        knowledge={"iere": {"ranked_evidence": [], "ask_envelope": {}}},
    )
    sel = select_frameworks(
        question=q,
        intent_v2=irl["intent"],
        concept_mode=True,
        answer_assembly=plan,
    )
    assert sel["framework_ids"]
    assert "FW_PB" in _ids(sel) or "FW_RESIDUAL_INCOME" in _ids(sel)


def test_research_office_records_framework_metadata() -> None:
    from research_office.publications.builders import build_company_note

    note = build_company_note("INFY", trigger_reason="ifse_test")
    assert "framework_used" in note
    assert isinstance(note.get("framework_used"), list)
    assert note.get("framework_version")
    assert "FW_DCF" in set(note.get("framework_used") or []) or "FW_EV_EBITDA" in set(
        note.get("framework_used") or []
    )


def test_dashboard_metrics() -> None:
    select(question="Why do banks trade on P/B?", intent_v2="Explain", concept_mode=True)
    dash = dashboard()
    assert dash["selection_count"] >= 1
    assert "framework_usage" in dash
    assert "wrong_framework_rate" in dash
    assert "multi_framework_usage" in dash
    assert "confidence_distribution" in dash


def test_no_llm_and_freeze_locks() -> None:
    forbidden = ("openai", "gemini", "anthropic", "generate_content", "ChatCompletion")
    for path in ROOT.rglob("*.py"):
        if "tests" in path.parts:
            continue
        src = path.read_text(encoding="utf-8")
        low = src.lower()
        for token in forbidden:
            assert token.lower() not in low, f"{path} mentions {token}"
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in {"eval", "exec"}
    meta = get_framework("FW_PB")
    assert meta and meta["replay_compatibility"] is True


# ---------------------------------------------------------------------------
# Sprint 3.3 — Framework Optimisation (cue overlays + sector enrichment)
# ---------------------------------------------------------------------------


def test_bank_risk_question_includes_risk_framework() -> None:
    sel = select_frameworks(
        question="Identify the top institutional risks for HDFCBANK that could invalidate a bullish thesis.",
        intent_v2="Analyse",
        ticker_hint="HDFCBANK",
    )
    ids = _ids(sel)
    assert sel["sector"] == "banks"
    assert "FW_RISK" in ids
    assert "FW_SCENARIO" in ids
    assert "FW_PB" in ids or "FW_RESIDUAL_INCOME" in ids
    assert "FW_EV_EBITDA" not in ids


def test_document_question_includes_governance() -> None:
    sel = select_frameworks(
        question="Using HDFCBANK's institutional documents, how would you use the MD&A to identify emerging risks?",
        intent_v2="Explain",
        ticker_hint="HDFCBANK",
    )
    ids = _ids(sel)
    assert "FW_CORPORATE_GOVERNANCE" in ids or "FW_RISK" in ids
    assert "FW_EV_EBITDA" not in ids


def test_it_services_enriched_composition() -> None:
    sel = select_frameworks(
        question="Which valuation frameworks are most appropriate for INFY (IT services) and why?",
        intent_v2="Explain",
        ticker_hint="INFY",
    )
    ids = _ids(sel)
    assert sel["sector"] == "it_services"
    assert "FW_DCF" in ids
    assert "FW_EV_EBITDA" in ids
    assert "FW_CASH_FLOW_QUALITY" in ids or "FW_BUSINESS_QUALITY" in ids


def test_nbfc_includes_risk_framework() -> None:
    sel = select_frameworks(
        question="Construct a risk checklist for regulatory action affecting BAJFINANCE.",
        intent_v2="Analyse",
        ticker_hint="BAJFINANCE",
    )
    ids = _ids(sel)
    assert sel["sector"] == "nbfc"
    assert "FW_RISK" in ids
    assert "FW_PB" in ids or "FW_RESIDUAL_INCOME" in ids


def test_airlines_fuel_yield_cues() -> None:
    sel = select_frameworks(
        question="How do ATF fuel cost and load factor affect Indigo airline operating leverage and competition?",
        intent_v2="Analyse",
        ticker_hint="INDIGO",
    )
    ids = _ids(sel)
    assert "FW_AVIATION_OPS" in ids
    assert "FW_EV_EBITDAR" in ids or "FW_MACRO_TRANSMISSION" in ids
