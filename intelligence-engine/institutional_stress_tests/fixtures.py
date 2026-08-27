"""Deterministic fixtures for IST-01 (presentation / scoring only — not live facts)."""

from __future__ import annotations

from typing import Any


def fire_prebuilt(ticker: str = "KOTAKBANK") -> dict[str, dict[str, Any]]:
    """Pass-through FIRE boards for orchestration tests — illustrative structure only."""
    return {
        "FIRE-01": {
            "ticker": ticker,
            "confidence": 0.72,
            "evidence_ids": ["ist01:f01:1"],
            "narrative": "Post-restriction financial trends (fixture).",
            "as_of": "2024-04-01T00:00:00+00:00",
        },
        "FIRE-02": {
            "ticker": ticker,
            "confidence": 0.68,
            "evidence_ids": ["ist01:f02:1"],
            "drivers": ["liability_franchise", "digital_onboarding"],
        },
        "FIRE-03": {
            "ticker": ticker,
            "confidence": 0.7,
            "evidence_ids": ["ist01:f03:1"],
            "strategy": "remediation_and_compliance",
        },
        "FIRE-04": {
            "ticker": ticker,
            "confidence": 0.65,
            "evidence_ids": ["ist01:f04:1"],
            "alignment": "partial",
        },
        "FIRE-05": {
            "ticker": ticker,
            "confidence": 0.62,
            "evidence_ids": ["ist01:f05:1"],
            "execution_score": 0.58,
        },
        "FIRE-06": {
            "ticker": ticker,
            "confidence": 0.74,
            "evidence_ids": ["ist01:f06:1"],
            "quality_score": 0.71,
            "pillars": {"franchise": 0.75, "risk": 0.68},
        },
        "CIO-01": {
            "ticker": ticker,
            "peers": ["HDFCBANK", "ICICIBANK", "AXISBANK"],
            "confidence": 0.7,
            "evidence_ids": ["ist01:cio:1"],
            "comparison_type": "relative_quality_post_event",
        },
    }


def complete_answers() -> dict[str, Any]:
    """Full 12-question institutional package (fixture — not a live research note)."""
    view = {
        "investment_thesis": (
            "An institutional investor should treat April 2024 as a monitoring and "
            "evidence-gathering window rather than an immediate directional call. "
            "The decision hinges on whether remediation is temporary/operational versus "
            "structural franchise damage — still incompletely evidenced."
        ),
        "evidence_supporting": [
            {
                "claim": "Franchise quality metrics may stabilize if remediation executes",
                "evidence_ids": ["ist01:f06:1", "ist01:f05:1"],
                "module": "FIRE-06",
            },
            {
                "claim": "Peer relative positioning can clarify whether the shock is idiosyncratic",
                "evidence_ids": ["ist01:cio:1"],
                "module": "CIO-01",
            },
        ],
        "evidence_against": [
            {
                "claim": "Regulatory restrictions can impair near-term growth and liability momentum",
                "evidence_ids": ["ist01:f01:1", "ist01:f02:1"],
                "module": "FIRE-01",
            },
            {
                "claim": "Management narrative may only partially align with financial evidence",
                "evidence_ids": ["ist01:f04:1"],
                "module": "FIRE-04",
            },
        ],
        "remaining_unknowns": [
            "Duration and full scope of RBI restrictions as disclosed over subsequent periods",
            "Pace of digital onboarding remediation versus peer digital acquisition",
            "Whether deposit/liability mix shifts prove temporary or structural",
        ],
        "confidence": {
            "mean_confidence": 0.58,
            "calibration_notes": (
                "Moderate confidence only — contradictory evidence present and several "
                "post-event periods still require monitoring."
            ),
        },
        "evidence_references": [
            {"evidence_id": "ist01:f01:1", "module": "FIRE-01"},
            {"evidence_id": "ist01:f02:1", "module": "FIRE-02"},
            {"evidence_id": "ist01:f03:1", "module": "FIRE-03"},
            {"evidence_id": "ist01:f04:1", "module": "FIRE-04"},
            {"evidence_id": "ist01:f05:1", "module": "FIRE-05"},
            {"evidence_id": "ist01:f06:1", "module": "FIRE-06"},
            {"evidence_id": "ist01:cio:1", "module": "CIO-01"},
        ],
        "questions_requiring_monitoring": [
            "Do subsequent disclosures show restriction relief with stable asset quality?",
            "Does FIRE-05 show remediation milestones delivered on stated timelines?",
            "Does CIO-01 show relative business quality gap closing or widening vs HDFC/ICICI/Axis?",
        ],
        "collapsed_to_buy_sell": False,
        "recommendation": None,
    }

    def q(text: str, evidence_ids: list[str], **extra: Any) -> dict[str, Any]:
        return {"status": "answered", "text": text, "evidence_ids": evidence_ids, **extra}

    return {
        "what_happened": q(
            "RBI imposed business restrictions on Kotak Mahindra Bank around April 2024; "
            "disclosures and subsequent statements define the event window for analysis.",
            ["ist01:fil:event"],
        ),
        "what_caused_it": q(
            "Causes centre on supervisory/IT and compliance concerns cited in regulatory "
            "and management disclosures — to be traced via FIL + FIRE-03, not assumed.",
            ["ist01:f03:1"],
        ),
        "temporary_or_structural": q(
            "Open question: operational/IT remediation could be temporary; franchise or "
            "liability franchise damage would be more structural — FIRE-01/02/06 must track both paths.",
            ["ist01:f01:1", "ist01:f06:1"],
        ),
        "management_diagnosis": q(
            "Compare management diagnosis (FIRE-03) against financial evidence alignment (FIRE-04).",
            ["ist01:f03:1", "ist01:f04:1"],
        ),
        "execution_vs_promises": q(
            "FIRE-05 must track whether remediation milestones were delivered versus promised.",
            ["ist01:f05:1"],
        ),
        "financial_quality_evolution": q(
            "FSE + FIRE-01 + FIRE-06 should show whether earnings quality and franchise metrics "
            "improved or deteriorated across the post-restriction window.",
            ["ist01:f01:1", "ist01:f06:1"],
        ),
        "competitor_performance": q(
            "CIO-01 comparison versus HDFCBANK, ICICIBANK, AXISBANK over the same period.",
            ["ist01:cio:1"],
        ),
        "relative_business_quality": q(
            "Relative FIRE-06 quality versus peers determines whether Kotak lost or gained ground.",
            ["ist01:f06:1", "ist01:cio:1"],
        ),
        "evidence_against": q(
            "Growth impairment risk, partial evidence alignment, and peer outperformance possibilities.",
            ["ist01:f01:1", "ist01:f04:1"],
            items=["restriction_drag", "alignment_gap"],
        ),
        "evidence_supporting": q(
            "Potential stabilization if remediation executes; idiosyncratic vs sector shock via peers.",
            ["ist01:f05:1", "ist01:cio:1"],
            items=["remediation_option", "idiosyncratic_path"],
        ),
        "missing_evidence": q(
            "Full restriction timeline, deposit mix path, and peer digital acquisition deltas remain incomplete.",
            [],
            items=[
                "complete_restriction_timeline",
                "deposit_mix_path",
                "peer_digital_acquisition_delta",
            ],
        ),
        "final_institutional_view": view,
    }


def buy_without_evidence_answers() -> dict[str, Any]:
    """Automatic-failure fixture: Buy Kotak with no supporting evidence."""
    return {
        "what_happened": {"status": "answered", "text": "RBI restricted Kotak.", "evidence_ids": []},
        "final_institutional_view": {
            "investment_thesis": "Buy Kotak immediately after the RBI restrictions.",
            "evidence_supporting": [],
            "evidence_against": [],
            "remaining_unknowns": [],
            "confidence": {"mean_confidence": 0.9},
            "evidence_references": [],
            "questions_requiring_monitoring": [],
            "collapsed_to_buy_sell": True,
            "recommendation": "BUY",
        },
    }
