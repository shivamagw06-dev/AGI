"""Business Analyst V2.1 — institutional learning assets."""

from __future__ import annotations

from institutional_analysts.business.analyst import analyse
from institutional_analysts.business.brain import IAI_BUSINESS_VERSION, think
from institutional_analysts.business.brain.business_dna import get_dna, reset_for_tests as reset_dna
from institutional_analysts.business.brain.case_library import FAILURE_CASES, SUCCESS_CASES
from institutional_analysts.business.brain.memory import get_timeline, quality_series, reset_for_tests as reset_ba_mem
from institutional_analysts.flags import is_iai_business_v2_1_enabled
from institutional_analysts.memory import reset_for_tests


def _hdfc_evidence():
    return {
        "company": "HDFC Bank",
        "ticker": "HDFCBANK",
        "business_model": "Universal bank franchise funded by low-cost deposits",
        "advantages": [
            "Distribution scale",
            "Brand trust",
            "Low-cost deposit franchise",
            "Network reach",
        ],
        "revenue_drivers": ["Deposit franchise", "Retail credit"],
        "competitive_position": "Private banking",
        "pricing_power": "Franchise pricing power in retail liabilities",
        "brand": "High-trust retail franchise",
        "capital_allocation": "Disciplined reinvestment and conservative underwriting",
        "growth_opportunities": ["Share gains", "Retail product deepening"],
        "business_risks": ["Deposit competition", "Regulatory change", "NIM pressure"],
        "business_quality_score": 83,
        "documents_used": ["Annual report commentary"],
        "evidence_refs": [
            {"claim": "Low-cost deposit franchise", "source_ref": "institutional research"},
            {"claim": "Deposit competition", "source_ref": "institutional research"},
        ],
    }


def setup_function():
    reset_for_tests()
    reset_dna()
    reset_ba_mem()


def test_v2_1_flag_and_version():
    assert is_iai_business_v2_1_enabled() is True
    assert IAI_BUSINESS_VERSION == "iai-business-v2.1.0"


def test_case_library_populated():
    assert any(c["id"] == "apple" for c in SUCCESS_CASES)
    assert any(c["id"] == "nokia" for c in FAILURE_CASES)
    assert any(c["id"] == "kingfisher" for c in FAILURE_CASES)


def test_learning_chain_and_hdfc_trajectory_language():
    out = think(
        company="HDFC Bank",
        evidence=_hdfc_evidence(),
        confidence={"evidence": 0.72, "knowledge": 0.74, "freshness": 0.7, "overall": 0.72},
        ticker="HDFCBANK",
    )
    assert out["learning_chain"] == [
        "knowledge",
        "frameworks",
        "case_studies",
        "historical_outcomes",
        "lessons_learned",
        "reasoning",
        "opinion",
    ]
    assert out["case_studies"]["success_cases"]
    assert out["case_studies"]["counter_cases"]
    assert out["case_studies"]["resemblance"]
    assert out["archetype"]["primary"]["name"]
    assert out["historical_outcomes"]["timeline"]
    assert any(e.get("event") == "Deposit competition" for e in out["historical_outcomes"]["timeline"])
    assert out["lessons_learned"]
    assert out["business_dna"]["moat"]
    assert out["business_dna"]["pricing_power"]

    eo = (out.get("executive_opinion") or "").lower()
    assert "no longer strengthening" in eo or "deposit competition" in eo
    assert "structurally" in eo or "durable" in eo or "own" in eo

    # Quality path meaningful
    path = out["business_quality"].get("quality_path") or []
    assert len(path) >= 3
    assert path[0].get("year") == 2018


def test_business_dna_persists_and_updates():
    think(company="HDFC Bank", evidence=_hdfc_evidence(), ticker="HDFCBANK",
          confidence={"evidence": 0.7, "knowledge": 0.7, "freshness": 0.7, "overall": 0.7})
    dna1 = get_dna("HDFCBANK")
    assert dna1 is not None
    assert dna1.get("summary")

    evidence2 = _hdfc_evidence()
    evidence2["business_quality_score"] = 70
    evidence2["business_risks"] = ["Deposit competition", "Regulatory change", "Credit cycle", "Technology"]
    think(
        company="HDFC Bank",
        evidence=evidence2,
        ticker="HDFCBANK",
        confidence={"evidence": 0.65, "knowledge": 0.65, "freshness": 0.65, "overall": 0.65},
    )
    dna2 = get_dna("HDFCBANK")
    assert dna2 is not None
    # Second pass recorded
    assert get_timeline("HDFCBANK")
    assert len(get_timeline("HDFCBANK")) >= 2


def test_opinion_timeline_quality_series():
    for score in (78, 81, 76):
        ev = _hdfc_evidence()
        ev["business_quality_score"] = score
        think(
            company="HDFC Bank",
            evidence=ev,
            ticker="HDFCBANK",
            confidence={"evidence": 0.7, "knowledge": 0.7, "freshness": 0.7, "overall": 0.7},
        )
    series = quality_series("HDFCBANK")
    # Same calendar year collapses — at least one point recorded
    assert series or get_timeline("HDFCBANK")


def test_analyse_surfaces_learning_fields():
    op = analyse(
        {
            "ticker": "HDFCBANK",
            "company_analysis": {
                "company_name": "HDFC Bank",
                "business_quality": {
                    "business_quality_score": 83,
                    "revenue_drivers": ["Deposit franchise", "Retail credit"],
                    "competitive_advantages": [
                        "Distribution scale",
                        "Brand trust",
                        "Low-cost deposit franchise",
                    ],
                    "pricing_power": "Franchise pricing power",
                    "brand": "High-trust retail franchise",
                    "capital_allocation": "Disciplined conservative capital allocation",
                    "confidence": 0.74,
                    "risks": ["Deposit competition", "NIM pressure"],
                },
            },
            "company_dossier": {
                "identity": {"company_name": "HDFC Bank", "industry": "Private banking"},
                "business_profile": {"business_model": "Universal bank franchise"},
            },
            "live_evidence": {"documents_used": ["Annual report commentary"], "freshness_score": 0.7},
        }
    )
    assert op.get("iai_v2_1") is True
    assert op.get("case_studies")
    assert op.get("business_dna")
    assert op.get("lessons_learned")
    assert op.get("historical_outcomes")
    assert "Nokia" in str(op.get("case_studies")) or "Apple" in str(op.get("case_studies")) or op["case_studies"].get(
        "resemblance"
    )
