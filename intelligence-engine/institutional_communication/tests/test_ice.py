"""AGIB v3.4 Track D — ICE acceptance tests."""

from __future__ import annotations

import ast
from pathlib import Path

from institutional_communication import ICE_VERSION, communicate, communicate_from_ask
from institutional_communication.production import dashboard, health
from institutional_communication.schema import MANDATORY_SECTIONS, TEMPLATES

ROOT = Path(__file__).resolve().parents[1]


def _sample_ia(**over):
    base = {
        "format": "institutional_answer_v1",
        "question": "Explain why EV/EBITDA is generally inappropriate for banks.",
        "intent_v2": "Explain",
        "question_type": "education",
        "concept_mode": True,
        "as_of": None,
        "sections": {
            "executive_summary": {"bullets": ["Intent: Explain", "Concept mode"], "evidence_ids": ["e1"]},
            "evidence": {"bullets": ["[Accounting] Bank book equity"], "evidence_ids": ["e1"]},
            "analysis": {"bullets": ["Analyse via Accounting evidence"], "evidence_ids": ["e1"]},
            "framework": {"bullets": ["Framework input domain: Accounting"], "evidence_ids": ["e1"]},
            "risks": {"bullets": ["Evidence gap: none material"], "evidence_ids": []},
            "conclusion": {"bullets": ["Education path"], "evidence_ids": ["e1"]},
            "confidence": {"bullets": ["Band: High"], "evidence_ids": []},
            "sources": {"bullets": ["e1: source=iere"], "evidence_ids": ["e1"]},
        },
        "evidence": {
            "items": [
                {
                    "evidence_id": "e1",
                    "evidence_type": "ACCOUNTING_NOTES",
                    "title": "Bank book equity accounting",
                    "source": "iere",
                    "document_id": "doc1",
                }
            ],
            "iere_ranked_count": 1,
            "retrieval_id": "ret1",
        },
        "frameworks": {
            "framework_ids": ["FW_FRAMEWORK_EXPLANATION", "FW_PB", "FW_RESIDUAL_INCOME"],
            "primary": [
                {"framework_id": "FW_PB", "name": "Price to Book", "role": "primary"},
                {"framework_id": "FW_RESIDUAL_INCOME", "name": "Residual Income", "role": "primary"},
            ],
            "secondary": [{"framework_id": "FW_ROE", "name": "ROE", "role": "secondary"}],
            "supporting": [],
            "forbidden_rejected": ["FW_EV_EBITDA"],
            "explanation": {
                "reason": (
                    "The entity/context is a regulated bank with book value as the principal "
                    "anchor of value. EV/EBITDA is explicitly excluded by the framework registry."
                ),
                "confidence": {"pct": 92, "band": "High"},
            },
            "confidence": {"band": "High", "pct": 92, "score": 0.92},
            "sector": "banks",
        },
        "gaps": {
            "missing_domains": [],
            "coverage": 1.0,
            "tell_reasoning": "Required domains present or softened.",
            "confidence_penalty": 0.0,
        },
        "confidence": {"band": "High", "score": 0.9, "coverage": 1.0, "pct": 90},
        "citations": {
            "flat": [
                {
                    "evidence_id": "e1",
                    "source": "iere",
                    "document_id": "doc1",
                    "knowledge_object": "ACCOUNTING_NOTES",
                    "replay_id": "ret1",
                    "as_of": None,
                }
            ]
        },
        "risk_signals": {
            "missing_domains": [],
            "tell_reasoning": "Required domains present or softened.",
            "disagreements": [],
        },
        "replay": {"retrieval_id": "ret1", "ranked_count": 1},
        "fabricated": False,
    }
    base.update(over)
    return base


def test_ice_version_and_health() -> None:
    assert ICE_VERSION.startswith("institutional-communication")
    assert health()["status"] == "ok"
    assert set(TEMPLATES)


def test_educational_template_and_framework_visible() -> None:
    out = communicate(_sample_ia())
    assert out["template"] == "educational"
    assert out["framework_visible"] is True
    assert "framework_used" in out["sections"]
    text = out["prose"].lower()
    assert "residual income" in text or "price to book" in text
    assert "ev/ebitda" in text or "fw_ev_ebitda" in text
    assert (out.get("validation") or {}).get("passed") is True
    assert out["llm_used"] is False
    assert out["reasoning_changed"] is False


def test_mandatory_sections_present() -> None:
    out = communicate(_sample_ia())
    for name in MANDATORY_SECTIONS:
        assert name in out["sections"], name
        assert out["sections"][name]["bullets"], name


def test_evidence_before_conclusions_in_order() -> None:
    out = communicate(_sample_ia())
    order = out["section_order"]
    assert order.index("evidence") < order.index("analysis")
    assert order.index("framework_used") < order.index("analysis") or order.index("framework_used") < order.index(
        "confidence"
    )


def test_macro_template() -> None:
    out = communicate(
        _sample_ia(
            intent_v2="Macro",
            question="Trace repo rate transmission",
            frameworks={
                "framework_ids": ["FW_MACRO_TRANSMISSION"],
                "primary": [
                    {
                        "framework_id": "FW_MACRO_TRANSMISSION",
                        "name": "Macro Transmission",
                        "role": "primary",
                    }
                ],
                "secondary": [],
                "supporting": [],
                "forbidden_rejected": [],
                "explanation": {"reason": "Macro questions use transmission framework."},
                "confidence": {"band": "High", "pct": 88},
            },
        )
    )
    assert out["template"] == "macro_analysis"
    assert "macro transmission" in out["prose"].lower()


def test_historical_replay_template() -> None:
    out = communicate(
        _sample_ia(
            intent_v2="HistoricalReplay",
            as_of="2020-03-31",
            question="Replay Infosys as of 31 March 2020",
            concept_mode=False,
        )
    )
    assert out["template"] == "historical_replay"
    for name in (
        "historical_context",
        "replay_timestamp",
        "available_evidence",
        "future_leakage_check",
    ):
        assert name in out["sections"]
    assert "2020-03-31" in out["prose"]
    assert "current pe" not in out["prose"].lower()


def test_company_analysis_template() -> None:
    out = communicate(_sample_ia(intent_v2="Analyse", concept_mode=False, question_type="business_quality"))
    assert out["template"] == "company_analysis"


def test_no_generic_markers() -> None:
    bad = _sample_ia()
    bad["sections"]["executive_summary"]["bullets"] = [
        "the company continues to show business strength rated C"
    ]
    out = communicate(bad)
    # ICE must strip / not emit generic markers in executive
    assert "business strength rated c" not in (out.get("executive_summary") or "").lower()
    assert "valuation question blocked" not in (out.get("prose") or "").lower()


def test_ask_pipeline_soft_wire() -> None:
    from ask_pipeline.pipeline import run_complete_ask

    out = run_complete_ask(
        "Explain why EV/EBITDA is generally inappropriate for banks and insurance companies.",
        ticker_hint="INFY",
    )
    assert out.get("institutional_communication_version", "").startswith("institutional-communication")
    comm = out.get("communication") or {}
    assert comm.get("template") == "educational"
    assert comm.get("framework_visible") is True
    assert "framework_used" in (comm.get("sections") or {})
    assert out.get("answer", {}).get("source") == "institutional_communication"
    assert out.get("reasoning_changed") is False
    assert out.get("llm_synthesis_used") is False
    # Concept mode — no Infosys in ICE executive
    assert "infosys" not in (comm.get("executive_summary") or "").lower()


def test_answer_assembly_and_framework_consumed() -> None:
    from ask_pipeline.answer_assembly import assemble_answer_plan
    from ask_pipeline.intent_resolution import resolve_intent
    from framework_selection import select_frameworks

    q = "Why do banks trade on P/B?"
    irl = resolve_intent(q)
    aa = assemble_answer_plan(
        question=q,
        intent_v2=irl["intent"],
        intent_resolution=irl,
        knowledge={
            "iere": {
                "ranked_evidence": [
                    {
                        "evidence_id": "e_pb",
                        "evidence_type": "HISTORICAL_VALUATION",
                        "title": "Bank P/B series",
                        "source": "iere",
                        "rank_score": 0.9,
                        "citation": {"source": "iere", "document_id": "d1"},
                    }
                ],
                "ask_envelope": {},
                "retrieval_id": "r1",
                "ranked_count": 1,
            }
        },
    )
    fs = select_frameworks(question=q, intent_v2=irl["intent"], concept_mode=True)
    out = communicate_from_ask(
        question=q,
        intent_resolution=irl,
        answer_assembly=aa,
        framework_selection=fs,
        institutional_answer={"sections": (aa.get("skeleton") or {}).get("sections") or {}},
        knowledge={"iere": {"ranked_evidence": aa and [], "ask_envelope": {"top_evidence": []}, "ranked_count": 1}},
    )
    assert out["consumes_institutional_answer"] is True
    assert "FW_PB" in str(out.get("institutional_answer", {}).get("framework_ids") or fs.get("framework_ids"))
    assert out["sections"]["evidence"]["bullets"]
    assert out["sections"]["confidence"]["bullets"]


def test_research_office_consumes_ice_template() -> None:
    from research_office.publications.builders import build_company_note

    note = build_company_note("INFY", trigger_reason="ice_test")
    comm = (note.get("body") or {}).get("communication") or {}
    assert comm.get("ice_version", "").startswith("institutional-communication")
    assert comm.get("template")
    assert comm.get("framework_visible") is True or bool(note.get("framework_used"))


def test_dashboard_metrics() -> None:
    communicate(_sample_ia())
    dash = dashboard()
    assert dash["communication_count"] >= 1
    assert "template_used" in dash
    assert "framework_visibility" in dash
    assert "narrative_completeness" in dash


def test_no_llm_and_freeze() -> None:
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
