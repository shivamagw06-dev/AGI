"""AGIB v3.4 Track B — Institutional Answer Assembly Engine tests."""

from __future__ import annotations

import ast
from pathlib import Path

from ask_pipeline.answer_assembly import AAE_VERSION, assemble_answer_plan, bind_reasoning_to_answer
from ask_pipeline.answer_assembly.classify import classify_evidence
from ask_pipeline.answer_assembly.gaps import detect_gaps
from ask_pipeline.answer_assembly.ordering import order_evidence
from ask_pipeline.answer_assembly.schema import DOMAIN_PRIORITY, SKELETON_SECTIONS
from ask_pipeline.intent_resolution import resolve_intent

ROOT = Path(__file__).resolve().parents[2]


def _sample_iere() -> list[dict]:
    return [
        {
            "evidence_id": "e_fin_1",
            "evidence_type": "FINANCIAL_METRICS",
            "title": "Bank book value and ROE series",
            "source": "iere",
            "rank_score": 0.91,
            "citation": {"source": "iere", "document_id": "doc_fin"},
        },
        {
            "evidence_id": "e_acct_1",
            "evidence_type": "ACCOUNTING_NOTES",
            "title": "Accounting treatment of bank equity",
            "source": "iere",
            "rank_score": 0.88,
            "citation": {"source": "iere", "document_id": "doc_acct"},
        },
        {
            "evidence_id": "e_val_1",
            "evidence_type": "HISTORICAL_VALUATION",
            "title": "Why banks trade on P/B and residual income",
            "source": "iere",
            "rank_score": 0.86,
            "citation": {"source": "iere", "document_id": "doc_val"},
        },
        {
            "evidence_id": "e_macro_1",
            "evidence_type": "MACRO_INDICATORS",
            "title": "Repo rate path",
            "source": "iere",
            "rank_score": 0.70,
            "citation": {"source": "iere", "document_id": "doc_macro"},
        },
    ]


def test_aae_version() -> None:
    assert AAE_VERSION.startswith("answer-assembly")


def test_classify_domains() -> None:
    classified = classify_evidence(iere_items=_sample_iere(), intent_v2="Explain")
    assert classified["item_count"] == 4
    assert "Financial" in classified["by_domain"]
    assert "Accounting" in classified["by_domain"]
    # Title cue promotes valuation framework
    assert "ValuationFramework" in classified["by_domain"]


def test_education_prioritises_framework_before_macro() -> None:
    classified = classify_evidence(iere_items=_sample_iere(), intent_v2="Education")
    ordered = order_evidence(classified, intent_v2="Education")
    domains = [i["domain"] for i in ordered["ordered"]]
    assert domains.index("ValuationFramework") < domains.index("Macro")
    assert domains.index("Accounting") < domains.index("Macro")
    assert DOMAIN_PRIORITY["Education"][0] == "ValuationFramework"


def test_gap_detection_reduces_coverage() -> None:
    empty = classify_evidence(iere_items=[], intent_v2="Education")
    gaps = detect_gaps(empty, intent_v2="Education")
    assert "ValuationFramework" in gaps["missing_domains"]
    assert gaps["coverage"] < 1.0
    assert "reduce confidence" in gaps["tell_reasoning"].lower()

    soft = classify_evidence(iere_items=_sample_iere()[:1], intent_v2="Education")
    soft_gaps = detect_gaps(soft, intent_v2="Education")
    # Financial softens Accounting / ValuationFramework requirements
    assert soft_gaps["softened_domains"] or soft_gaps["coverage"] >= gaps["coverage"]


def test_assemble_plan_skeleton_and_citations() -> None:
    q = "Explain why EV/EBITDA is generally inappropriate for banks and insurance companies."
    irl = resolve_intent(q, ticker_hint="INFY")
    plan = assemble_answer_plan(
        question=q,
        intent_v2=irl["intent"],
        evidence={"packs": {}},
        knowledge={
            "iere": {
                "retrieval_id": "ret_test",
                "ranked_evidence": _sample_iere(),
                "ask_envelope": {"top_evidence": _sample_iere()[:2]},
            }
        },
        intent_resolution=irl,
    )
    assert plan["ok"] is True
    assert plan["llm_used"] is False
    assert plan["fabricated"] is False
    sk = plan["skeleton"]
    assert sk["section_order"] == list(SKELETON_SECTIONS)
    assert sk["free_form"] is False
    assert plan["citations"]["mapped_count"] >= 1
    assert plan["confidence"]["band"] in {"High", "Moderate", "Low", "Insufficient"}
    assert plan["answer_plan"]["concept_mode"] is True


def test_bind_reasoning_fills_skeleton() -> None:
    q = "Why do banks trade on P/B?"
    plan = assemble_answer_plan(
        question=q,
        intent_v2="Explain",
        knowledge={"iere": {"ranked_evidence": _sample_iere(), "ask_envelope": {}}},
        intent_resolution={"concept_mode": True, "evidence_requirements": {}},
    )
    bound = bind_reasoning_to_answer(
        plan,
        governance={
            "path": "education",
            "question_type": "education",
            "committee": {
                "stance": "explain",
                "conclusion": "Banks are book-value businesses; EV/EBITDA is inappropriate.",
                "findings": [{"finding": "Deposit franchise drives P/B"}],
                "disagreements": [],
            },
        },
    )
    ans = bound["institutional_answer"]
    assert ans["format"] == "institutional_skeleton_v1"
    assert ans["generic"] is False
    assert "executive_summary" in ans["sections"]
    assert any("Governance path" in b for b in ans["sections"]["executive_summary"]["bullets"])
    assert ans["sections"]["conclusion"]["bullets"]


def test_no_llm_ranking_or_synthesis_in_package() -> None:
    """Static scan: Track B modules must not call OpenAI/Gemini for ranking/synthesis."""
    root = ROOT / "answer_assembly"
    forbidden = ("openai", "gemini", "anthropic", "ChatCompletion", "generate_content")
    for path in root.rglob("*.py"):
        if "tests" in path.parts:
            continue
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src)
        text = src.lower()
        for token in forbidden:
            assert token.lower() not in text, f"{path} mentions {token}"
        # No dynamic exec/eval
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in {"eval", "exec"}


def test_pipeline_soft_wire_exposes_institutional_answer() -> None:
    from ask_pipeline.pipeline import run_complete_ask

    out = run_complete_ask(
        "Explain why EV/EBITDA is generally inappropriate for banks and insurance companies.",
        ticker_hint="INFY",
    )
    assert out.get("answer_assembly_version", "").startswith("answer-assembly")
    aa = out.get("answer_assembly") or {}
    assert aa.get("ok") is True
    assert aa.get("llm_used") is False
    assert aa.get("skeleton", {}).get("section_order")
    inst = out.get("institutional_answer") or {}
    assert inst.get("format") == "institutional_skeleton_v1"
    assert out.get("concept_mode") is True
    assert out.get("llm_synthesis_used") is False
    assert "confidence" in aa


def test_macro_concept_orders_macro_before_financial() -> None:
    items = [
        {
            "evidence_id": "m1",
            "evidence_type": "MACRO_INDICATORS",
            "title": "Inflation transmission",
            "rank_score": 0.8,
            "citation": {"source": "iere"},
        },
        {
            "evidence_id": "f1",
            "evidence_type": "FINANCIAL_METRICS",
            "title": "Company EPS",
            "rank_score": 0.95,
            "citation": {"source": "iere"},
        },
        {
            "evidence_id": "g1",
            "evidence_type": "GOVERNMENT_POLICIES",
            "title": "RBI policy",
            "rank_score": 0.75,
            "citation": {"source": "iere"},
        },
    ]
    classified = classify_evidence(iere_items=items, intent_v2="Macro")
    ordered = order_evidence(classified, intent_v2="Macro")
    domains = [i["domain"] for i in ordered["ordered"]]
    assert domains.index("Macro") < domains.index("Financial")
    assert domains.index("Government") < domains.index("Financial")
