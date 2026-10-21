"""Investment Committee Intelligence V1 — deliberation / vote / minutes tests."""

from __future__ import annotations

from institutional_analysts.memory import reset_for_tests as reset_iaf_memory
from institutional_analysts.production import package_for_ask_agi as iaf_package
from investment_committee.production import health, package_for_ask_agi, quality_gates, record_actuals
from investment_committee.schema import ICI_VERSION, OBJECT_TYPES
from investment_committee.store import reset_for_tests


def setup_function():
    reset_for_tests()
    reset_iaf_memory()


def _opinions() -> dict:
    def op(role, analyst, stance, conf, strengths, weaknesses, questions=None):
        return {
            "role": role,
            "analyst": analyst,
            "summary": f"{analyst} structured view.",
            "headline": f"{analyst} structured view.",
            "stance": stance,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "evidence": ["Institutional evidence pack", "Cross-check complete"],
            "unanswered_questions": questions or ["Need next print confirmation."],
            "confidence": {
                "evidence": conf,
                "knowledge": conf,
                "freshness": conf,
                "coverage": conf,
                "overall": conf,
            },
            "sections": {"roe": "16%", "revenue": "14%"},
            "structured": True,
        }

    return {
        "business": op(
            "business",
            "Business Analyst",
            "Bullish",
            0.83,
            ["Exceptionally strong franchise"],
            ["Competitive intensity"],
            ["Is market share actually rising?"],
        ),
        "financial": op(
            "financial",
            "Financial Analyst",
            "Bullish",
            0.82,
            ["Margins improving"],
            ["Cash conversion watch"],
        ),
        "valuation": op(
            "valuation",
            "Valuation Analyst",
            "Bearish",
            0.7,
            ["Peer triangulation available"],
            ["Market already prices growth"],
        ),
        "market": op("market", "Market Analyst", "Neutral", 0.55, ["Liquidity high"], ["Momentum mixed"]),
        "sector": op("sector", "Sector Analyst", "Bullish", 0.66, ["Attractive structure"], ["Regulation"]),
        "macro": op("macro", "Macro Analyst", "Neutral", 0.58, ["Rates stable"], ["Transmission lag"]),
        "risk": op("risk", "Risk Analyst", "Bearish", 0.6, ["Monitoring list"], ["Credit cycle", "Deposit competition"]),
        "management": op("management", "Management Analyst", "Bullish", 0.7, ["Governance solid"], ["Pledge watch"]),
        "ownership": op("ownership", "Ownership Analyst", "Neutral", 0.52, ["Promoter stable"], ["Float watch"]),
    }


def test_health_and_gates():
    h = health()
    assert h["status"] == "ok"
    assert h["version"] == ICI_VERSION
    assert h["not_an_engine"] is True
    assert "vote" in h["stages"]
    assert set(OBJECT_TYPES).issubset(set(h["object_types"]))
    g = quality_gates()
    assert g["passed"] is True
    assert g["checks"]["recommendation_is_vote_not_trade_ticket"] is True


def test_deliberation_hdfc_style_meeting():
    out = package_for_ask_agi(
        _opinions(),
        query="Should I invest in HDFC Bank?",
        company="HDFC Bank",
        ticker="HDFCBANK",
    )
    assert out["enabled"] is True
    assert out["meeting"] is True

    # Stage 1
    consensus = out["consensus"]
    assert consensus["type"] == "CommitteeConsensus"
    assert consensus["areas_of_agreement"]
    assert consensus["areas_of_disagreement"]
    assert consensus["areas_with_weak_evidence"] is not None
    assert consensus["areas_needing_review"]

    # Stage 2 — quality vs entry conflict explained
    conflicts = out["conflicts"]
    assert conflicts
    assert conflicts[0]["type"] == "CommitteeConflict"
    assert "assessment" in conflicts[0]["committee_assessment"].lower() or "quality" in conflicts[0]["committee_assessment"].lower()
    assert conflicts[0]["recommendation_confidence_impact"]

    # Stage 3 — challenges
    challenges = out["challenges"]
    assert challenges
    assert challenges[0]["type"] == "CommitteeChallenge"
    assert challenges[0]["open_evidence_request"]["type"] == "OpenEvidenceRequest"
    joined = " ".join(c["challenge"] for c in challenges).lower()
    assert "operating leverage" in joined or "market share" in joined

    # Stage 4 — dynamic confidence
    recalc = out["confidence_recalibration"]
    assert "financial" in recalc
    assert recalc["financial"]["submitted"] == 0.82
    assert recalc["financial"]["recalibrated"] < recalc["financial"]["submitted"]

    # Stage 5 — vote
    vote = out["vote"]
    assert vote["type"] == "CommitteeVote"
    assert vote["consensus"] in {"Constructive", "Neutral", "Cautious"}
    assert vote["conviction"] in {"High", "Moderate", "Low"}
    assert "/" in vote["tally"]

    # Stage 6 — minutes stored
    minutes = out["minutes"]
    assert minutes["type"] == "CommitteeMinutes"
    assert minutes["company"] == "HDFC Bank"
    assert minutes["question"]
    assert minutes["discussion"]
    assert minutes["decision"]
    assert minutes["open_questions"]
    assert "Buy" not in str(minutes.get("decision"))
    assert "Sell" not in str(minutes.get("decision"))

    # Stage 7 — minority
    assert out["minority_opinions"]
    assert out["minority_opinions"][0]["type"] == "MinorityOpinion"

    # Stage 8 — history/timeline
    assert out["history"]
    assert out["timeline"]

    # Stage 9 — accuracy object present
    assert out["accuracy"]["type"] == "CommitteeAccuracy"

    # Stage 10 — recommendation as vote, not trade ticket
    decision = out["decision"]
    assert decision["type"] == "CommitteeDecision"
    assert decision["committee_position"]
    assert decision["recommendation_readiness"]
    assert decision["not_a_trade_ticket"] is True
    assert decision["business_quality"]
    assert decision["valuation"]


def test_prediction_accountability():
    out = package_for_ask_agi(
        _opinions(),
        query="Should I invest in HDFC Bank?",
        company="HDFC Bank",
        ticker="HDFCBANK",
    )
    meeting_id = out["meeting_id"]
    preds = out.get("predictions") or []
    assert preds
    metric = preds[0]["metric"]
    expected = preds[0]["expected"]
    # Miss by ~27% so accuracy still scores a row (close_enough threshold is 25%)
    actual = float(expected) * 0.7
    review = record_actuals(
        "HDFCBANK",
        meeting_id=meeting_id,
        actuals=[{"metric": metric, "actual": actual}],
    )
    assert review["predictions_scored"] >= 1
    assert review["committee_accuracy_pct"] is not None


def test_iaf_soft_wires_ici():
    # Full Ask AGI path through IAF should carry ICI deliberation objects
    from institutional_analysts.production import package_for_ask_agi as iaf

    # Minimal ctx — reuse IAF hdfc-like through opinions generated by IAF
    pkg = iaf(
        "Should I invest in HDFC Bank?",
        ticker="HDFCBANK",
        company_analysis={
            "ticker": "HDFCBANK",
            "company_name": "HDFC Bank",
            "identity": {"company_name": "HDFC Bank", "business_model": "Bank"},
            "business_quality": {
                "business_quality_score": 80,
                "competitive_advantages": ["Scale"],
                "confidence": 0.8,
            },
            "financial_intelligence": {"trend": "Improving", "roe": "16%", "confidence": 0.8},
            "valuation_intelligence": {"pe": 24, "margin_of_safety": "Modest", "confidence": 0.6},
            "risks": ["Credit", "Deposit", "Regulation", "Asset quality"],
        },
        company_dossier={
            "ticker": "HDFCBANK",
            "identity": {"company_name": "HDFC Bank"},
            "market_data": {"trend": "Constructive", "liquidity": "High"},
            "shareholding": {"promoters": "Stable", "trend": "Stable"},
            "management": {"governance": "Solid board"},
        },
        valuation={"pe": 24, "margin_of_safety": "Modest"},
        sector_intelligence={"sector_id": "private_banks", "growth": "Attractive mid-cycle"},
        company_monitor={"what_changed": {"risks": ["Deposit competition"]}},
        institutional_briefing={"current_outlook": "Macro mildly supportive", "macro_drivers": ["Rates"]},
        decision_engine={
            "active": True,
            "layers": [
                {"id": "risk", "score": 40, "reasoning": "Risks live"},
                {"id": "management", "score": 72, "reasoning": "Execution solid"},
                {"id": "technical", "score": 55, "reasoning": "Tape mixed"},
                {"id": "macro", "score": 60, "reasoning": "Supportive"},
            ],
            "summary": {"confidence_pct": 65},
        },
    )
    assert pkg["enabled"] is True
    committee = pkg["committee"]
    assert committee.get("ici_enabled") is True
    assert committee.get("vote")
    assert committee.get("decision")
    assert committee.get("challenges")
    assert pkg.get("committee_vote")
    assert pkg.get("committee_decision")
    cio = pkg["cio"]
    assert cio.get("committee_vote") or cio.get("committee_decision")
    assert "Buy" not in (cio.get("executive_summary") or "")
    assert "Sell" not in (cio.get("executive_summary") or "")
