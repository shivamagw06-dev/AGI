"""Ask orchestration guards — ticker binding + framework-meta executive hygiene."""

from __future__ import annotations

from app.cae.planner import extract_entities, plan_query
from app.kip.extractors import looks_like_equity_ticker
from app.ui.ticker_guard import (
    accept_detected_ticker,
    alias_ticker_from_question,
    kip_title_bind,
    looks_like_framework_meta_executive,
)
from institutional_communication.renderers.engine import render_communication
from institutional_reasoning.evidence_contracts import resolve_entities


def test_prose_tokens_are_not_tickers():
    assert looks_like_equity_ticker("SUMMARIZE") is False
    assert looks_like_equity_ticker("WHAT") is False
    assert looks_like_equity_ticker("CAPEX") is False
    assert accept_detected_ticker("SUMMARIZE") is None
    assert accept_detected_ticker("JSWSTEEL") is None  # not in known set; reject soft pollution
    assert accept_detected_ticker("META") == "META"
    assert accept_detected_ticker("RELIANCE") == "RELIANCE"


def test_alias_binds_meta_and_rejects_summarize_primary():
    assert alias_ticker_from_question("What did Meta say in Q2 2026 about AI capex?") == "META"
    assert alias_ticker_from_question(
        "What is AGI view on Zen Technologies 295 crore defence order?"
    ) == "ZENTEC"
    ents, primary = extract_entities("Summarize India's mid-2026 equity outlook.".upper())
    assert primary is None
    assert "SUMMARIZE" not in ents
    plan = plan_query("Summarize India's mid-2026 equity outlook.")
    assert plan.primary_ticker is None


def test_resolve_entities_prefers_meta_over_theme_noise():
    resolved = resolve_entities("What did Meta say in Q2 2026 about AI capex?")
    assert resolved["resolved"] is True
    assert resolved["primary"]["entity_id"] == "META"


def test_ice_executive_is_not_framework_scaffolding():
    ia = {
        "format": "institutional_answer_v1",
        "question": "What is Reliance's business model?",
        "intent_v2": "Explain",
        "question_type": "business_quality",
        "concept_mode": False,
        "sections": {
            "executive_summary": {
                "bullets": ["Reliance earns cash across refining, retail, and digital."],
                "evidence_ids": ["e1"],
            },
            "analysis": {
                "bullets": ["Segment mix diversifies cyclical refining cash flows."],
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
            "framework_ids": ["FW_SOTP", "FW_FRAMEWORK_EXPLANATION"],
            "explanation": {"reason": "Multi-business groups require Sum-of-the-Parts."},
            "confidence": {"band": "Medium", "pct": 60},
        },
        "confidence": {"band": "Medium", "score": 0.6, "pct": 60},
        "playbook": {
            "playbook_id": "PB_SOTP",
            "playbook_name": "SOTP Conglomerate Valuation",
            "checklist": {"steps": []},
        },
        "gaps": {"missing_domains": [], "coverage": 1.0},
        "citations": {"flat": []},
    }
    out = render_communication(ia)
    exec_text = out.get("executive_summary") or ""
    assert looks_like_framework_meta_executive(exec_text) is False
    assert "frameworks applied" not in exec_text.lower()
    assert "playbook:" not in exec_text.lower()
    assert "reliance" in exec_text.lower() or "sum-of-the-parts" in exec_text.lower()


def test_framework_meta_detector():
    assert looks_like_framework_meta_executive(
        "Intent: Unknown · Template: Research Note Frameworks applied: FW_SOTP Playbook: SOTP "
        "— reasoning follows the analytical checklist."
    )
    assert not looks_like_framework_meta_executive(
        "Reliance operates refining, retail, and Jio digital platforms."
    )


class _FakeHit:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class _FakeKip:
    def __init__(self, hits):
        self._hits = hits

    def search(self, _query, *, mode="keyword", limit=5):
        return type("Resp", (), {"hits": self._hits[:limit]})()


def test_kip_title_bind_uses_research_title_overlap():
    kip = _FakeKip(
        [
            _FakeHit(
                title="Zen Technologies’ ₹295 Crore Defence Win Boosts Revenue Visibility — Execution Is Now the Key",
                score=0.54,
                tickers=[],
            )
        ]
    )
    bound = kip_title_bind(
        "What is AGI’s view on Zen Technologies’ ₹295 crore defence order?",
        kip,
    )
    assert bound == "ZENTEC"
