"""Institutional Analyst Framework V1.1 — mandates, structure, committee meeting, CIO editor."""

from __future__ import annotations

import re

from answer_construction.production import package_for_ask_agi as ac_package
from institutional_analysts.base import domain_scrub, scrub_public
from institutional_analysts.mandates import MANDATES
from institutional_analysts.memory import reset_for_tests
from institutional_analysts.production import health, package_for_ask_agi, quality_gates
from institutional_analysts.schema import ANALYST_ROLES, IAF_VERSION, SECTION_OWNERS
from investment_committee.store import reset_for_tests as reset_ici_store


INTERNAL_LEAKS = (
    "CID",
    "LEO",
    "IRP",
    "DVC",
    "ECP",
    "Yahoo",
    "Groww",
    "IndianAPI",
    "MarketDataClient",
    "Capital IQ",
    "Company Analysis",
    "Financial Intelligence",
)


def _hdfc_ctx(*, pe: float = 18.5, margin_of_safety: str = "Modest", biz_score: float = 78) -> dict:
    return {
        "query": "Should I invest in HDFC Bank?",
        "ticker": "HDFCBANK",
        "company_analysis": {
            "enabled": True,
            "ticker": "HDFCBANK",
            "company_name": "HDFC Bank",
            "identity": {"company_name": "HDFC Bank", "business_model": "Universal bank franchise"},
            "business_quality": {
                "business_quality_score": biz_score,
                "revenue_drivers": ["Deposit franchise", "Retail credit"],
                "competitive_advantages": ["Distribution scale", "Brand trust"],
                "confidence": 0.72,
            },
            "financial_intelligence": {
                "narrative": "Earnings quality supported by NIMs and fee income.",
                "trend": "Improving cash conversion",
                "roe": "16%",
                "confidence": 0.7,
            },
            "valuation_intelligence": {
                "pe": pe,
                "pb": 2.6,
                "margin_of_safety": margin_of_safety,
                "narrative": "Trades near historical mid-band versus growth.",
                "confidence": 0.62,
            },
            "risks": ["Credit cycle", "Regulatory capital", "Deposit competition", "Asset quality"],
            "catalysts": ["Next quarterly results"],
            "bull_case": ["Franchise share gains"],
            "bear_case": ["Asset-quality stress"],
        },
        "company_dossier": {
            "ticker": "HDFCBANK",
            "identity": {"company_name": "HDFC Bank"},
            "market_data": {"trend": "Constructive bias", "liquidity": "High"},
            "shareholding": {"promoters": "Stable", "fiis": "Material", "diis": "Rising", "trend": "Stable alignment"},
            "management": {"governance": "Institutional-grade board oversight"},
        },
        "finance_academy": {"applied_concepts": ["Franchise economics", "Cost of capital"]},
        "sector_intelligence": {
            "sector_id": "private_banks",
            "priority_metrics": ["NIM", "GNPA", "CASA"],
            "structure": "Oligopolistic private banking set",
            "growth": "Attractive mid-cycle credit growth",
        },
        "company_monitor": {"what_changed": {"risks": ["Deposit competition"], "monitor": ["NIM"]}},
        "valuation": {"pe": pe, "pb": 2.6, "margin_of_safety": margin_of_safety},
        "data_validation": {"confidence": 0.68, "checks": ["Statements validated"]},
        "knowledge_foundation": {"themes": ["Indian banking cycle"]},
        "institutional_briefing": {
            "macro_drivers": ["Policy rates", "Credit growth"],
            "macro_transmission": "Rates and liquidity transmit via NIMs and loan demand.",
            "current_outlook": "Macro mildly supportive",
        },
        "irp": {"macro": {"interest_rates": "Stable-to-easing bias", "inflation": "Moderating"}},
        "live_evidence": {"documents_used": ["Annual report commentary"], "sources_used": ["Policy updates"]},
        "decision_engine": {
            "active": True,
            "layers": [
                {"id": "macro", "score": 62, "reasoning": "Macro mildly supportive"},
                {"id": "technical", "score": 58, "reasoning": "Tape constructive but not decisive"},
                {"id": "risk", "score": 42, "reasoning": "Credit and regulatory risks remain live"},
                {"id": "management", "score": 70, "reasoning": "Execution track record solid"},
            ],
            "summary": {"confidence_pct": 68, "expected_return_12m_pct": 11},
        },
    }


def setup_function():
    reset_for_tests()
    reset_ici_store()


def test_health_and_gates():
    h = health()
    assert h["status"] == "ok"
    assert h["version"] == IAF_VERSION
    assert h["features"]["committee_meeting_stages"] is True
    assert h["features"]["disagreement_matrix"] is True
    assert len(h["mandates"]) == 9
    g = quality_gates()
    assert g["passed"] is True
    assert g["checks"]["mandate_metadata_present"] is True
    assert g["checks"]["cio_editor_no_analyst_verbatim"] is True


def test_all_nine_mandates():
    assert set(MANDATES) == set(ANALYST_ROLES)
    for role, meta in MANDATES.items():
        assert meta["mandate"]
        assert meta["primary_question"]
        assert meta["primary_inputs"]
        assert meta["outputs"]
        assert "Opinion" in " ".join(meta["outputs"]) or "Supporting Evidence" in meta["outputs"]


def test_domain_guard_business_cannot_talk_valuation():
    cleaned = domain_scrub("business", "PE looks attractive and the multiple is cheap")
    low = cleaned.lower()
    assert "pe" not in low
    assert "multiple" not in low
    assert "cheap" not in low


def test_domain_guard_financial_cannot_talk_moat():
    cleaned = domain_scrub("financial", "Brand moat and business model are excellent")
    low = cleaned.lower()
    assert "brand" not in low
    assert "moat" not in low
    assert "business model" not in low


def test_scrub_public_hides_internal_names():
    text = scrub_public("CID and LEO plus Yahoo and Groww and Company Analysis and Academy")
    lowered = text.lower()
    for leak in ("cid", "leo", "yahoo", "groww", "company analysis", "academy"):
        assert leak not in lowered


def test_hdfc_structured_opinions_committee_cio():
    pkg = package_for_ask_agi(**_hdfc_ctx(pe=24, margin_of_safety="Modest"))
    assert pkg["enabled"] is True
    assert pkg["version"] == IAF_VERSION
    opinions = pkg["analyst_opinions"]
    assert set(opinions) == set(ANALYST_ROLES)

    for role in ANALYST_ROLES:
        op = opinions[role]
        assert op["structured"] is True
        assert op["mandate"]["text"]
        assert op["mandate"]["primary_question"]
        assert op["mandate"]["primary_inputs"]
        assert op["summary"]
        assert op["stance"] in {"Bullish", "Neutral", "Bearish"}
        assert isinstance(op["strengths"], list)
        assert isinstance(op["weaknesses"], list)
        assert isinstance(op["evidence"], list)
        assert isinstance(op["unanswered_questions"], list)
        conf = op["confidence"]
        assert set(conf) >= {"evidence", "knowledge", "freshness", "coverage", "overall"}
        blob = " ".join(
            [
                str(op.get("summary") or ""),
                " ".join(op.get("strengths") or []),
                " ".join(op.get("weaknesses") or []),
                " ".join(op.get("evidence") or []),
            ]
        )
        for leak in INTERNAL_LEAKS:
            assert leak.lower() not in blob.lower(), f"{role} leaked {leak}"

    # Domain separation smoke (word-boundary — avoid matching "depends")
    biz_blob = (opinions["business"].get("summary") or "").lower()
    assert not re.search(r"\bp/?e\b", biz_blob)
    assert "multiple" not in biz_blob
    fin_blob = " ".join(opinions["financial"].get("strengths") or []).lower()
    assert "moat" not in fin_blob and "brand" not in fin_blob

    committee = pkg["committee"]
    assert committee["meeting"] is True
    assert committee["stage_1_consensus"]["business"] in {"Bullish", "Neutral", "Bearish"}
    assert isinstance(committee["stage_2_conflicts"], list)
    assert committee["stage_3_missing_evidence"]
    assert "Coverage" not in " ".join(committee["stage_3_missing_evidence"])
    matrix = committee["disagreement_matrix"]
    assert matrix["committee_stance"]
    assert matrix["reason"]
    assert matrix["analyst_stances"]
    minutes = committee["minutes"]
    assert minutes["title"] == "Investment Committee Minutes"
    assert minutes["decision"]
    assert pkg["committee_minutes"]

    # Quality vs entry conflict expected when biz bullish + valuation bearish
    assert any("entry" in (c.get("tension") or "").lower() or "quality" in (c.get("topic") or "").lower() for c in committee["stage_2_conflicts"])

    cio = pkg["cio"]
    assert cio["role"] == "editor"
    assert "HDFC" in (cio["executive_summary"] or "")
    assert cio["editor_rules"]["never_repeat_analyst_wording"] is True
    # CIO must not paste analyst summary verbatim
    for role, op in opinions.items():
        summary = (op.get("summary") or "").strip()
        if len(summary) > 40:
            assert summary not in (cio.get("executive_summary") or "")
            assert summary not in (cio.get("investment_thesis") or "")
    cio_blob = " ".join(
        [
            cio.get("executive_summary") or "",
            cio.get("investment_thesis") or "",
            cio.get("institutional_conclusion") or "",
        ]
    ).lower()
    for leak in INTERNAL_LEAKS + ("Academy",):
        assert leak.lower() not in cio_blob

    assert pkg["section_owners"] == SECTION_OWNERS
    assert pkg["disagreement_matrix"]


def test_analyst_memory_what_changed():
    reset_for_tests()
    first = package_for_ask_agi(**_hdfc_ctx(biz_score=78))
    assert first["analyst_opinions"]["business"]["what_changed"] is None
    second = package_for_ask_agi(**_hdfc_ctx(biz_score=40))
    changed = second["analyst_opinions"]["business"]["what_changed"]
    assert changed is not None
    assert changed["previous_stance"]
    assert changed["current_stance"]
    assert second["committee_minutes_history"]


def test_answer_construction_consumes_iaf():
    reset_for_tests()
    ctx = _hdfc_ctx()
    out = ac_package(
        query=ctx["query"],
        ticker=ctx["ticker"],
        company_analysis=ctx["company_analysis"],
        company_dossier=ctx["company_dossier"],
        finance_academy=ctx["finance_academy"],
        sector_intelligence=ctx["sector_intelligence"],
        company_monitor=ctx["company_monitor"],
        valuation=ctx["valuation"],
        data_validation=ctx["data_validation"],
        knowledge_foundation=ctx["knowledge_foundation"],
        institutional_briefing=ctx["institutional_briefing"],
        irp=ctx["irp"],
        live_evidence=ctx["live_evidence"],
        decision_engine=ctx["decision_engine"],
        executive="Placeholder executive",
        thesis="Placeholder thesis",
        house_label="Neutral",
        bull=[],
        bear=[],
        risks=[],
        catalysts=[],
        why=[],
    )
    assert out["enabled"] is True
    assert out["institutional_analysts_active"] is True
    iaf = out["institutional_analysts"]
    assert iaf.get("enabled") is True
    assert iaf.get("committee", {}).get("disagreement_matrix")
    assert iaf.get("committee_minutes")
    assert "HDFC" in (out["executive"] or "")
    assert out["bull"] and out["base"] and out["bear"]
    assert out["answer_policy"] in {
        "institutional_research_writer_publication_note",
        "institutional_analyst_framework_cio_report",
    }
