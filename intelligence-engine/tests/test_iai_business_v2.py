"""Institutional Analyst Intelligence — Business Analyst V2."""

from __future__ import annotations

from institutional_analysts.business.analyst import analyse
from institutional_analysts.business.brain import IAI_BUSINESS_VERSION, think
from institutional_analysts.business.brain.business_dna import reset_for_tests as reset_dna
from institutional_analysts.business.brain.memory import reset_for_tests as reset_ba_mem
from institutional_analysts.business.brain.quality_checks import run_checklist
from institutional_analysts.flags import is_iai_business_v2_enabled
from institutional_analysts.memory import put_opinion, reset_for_tests


REQUIRED_KEYS = (
    "executive_opinion",
    "business_quality",
    "moat",
    "competitive_position",
    "business_model",
    "revenue_drivers",
    "customer_economics",
    "pricing_power",
    "capital_allocation",
    "innovation",
    "industry_position",
    "growth_runway",
    "risks",
    "opportunities",
    "assumptions",
    "uncertainties",
    "missing_evidence",
    "confidence",
    "quality_checks",
)

LAZY_PHRASES = (
    "good company",
    "strong company",
    "nice moat",
    "the company manufactures",
)


def _rich_evidence(**overrides):
    base = {
        "company": "HDFC Bank",
        "business_model": "Universal bank franchise funded by low-cost deposits",
        "advantages": [
            "Distribution scale",
            "Brand trust",
            "Network reach",
            "Low-cost deposit franchise",
        ],
        "revenue_drivers": ["Deposit franchise", "Retail credit", "Fee income"],
        "competitive_position": "Leading private bank franchise",
        "pricing_power": "Franchise pricing power in retail liabilities and selective asset pricing",
        "brand": "High-trust retail franchise",
        "capital_allocation": "Disciplined reinvestment in franchise capacity with conservative underwriting",
        "growth_opportunities": ["Share gains", "Retail product deepening", "Digital distribution"],
        "business_risks": ["Deposit competition", "Regulatory change", "Credit cycle"],
        "business_quality_score": 78,
        "management": {"governance": "Institutional-grade board oversight"},
        "documents_used": ["Annual report commentary", "Investor presentation"],
        "global_peers": ["Global diversified bank franchises"],
        "indian_peers": ["Large private bank peers"],
        "evidence_refs": [
            {"claim": "Low-cost deposit franchise", "source_ref": "institutional research"},
            {"claim": "Annual report commentary", "source_ref": "institutional research"},
        ],
    }
    base.update(overrides)
    return base


def setup_function():
    reset_for_tests()
    reset_dna()
    reset_ba_mem()


def test_v2_flag_on():
    assert is_iai_business_v2_enabled() is True
    assert IAI_BUSINESS_VERSION.startswith("iai-business-v2")


def test_structured_object_keys_and_why_language():
    out = think(
        company="HDFC Bank",
        evidence=_rich_evidence(),
        confidence={"evidence": 0.72, "knowledge": 0.74, "freshness": 0.7, "overall": 0.72},
    )
    assert out["iai_version"] == IAI_BUSINESS_VERSION
    structured = out["structured_business_opinion"]
    for key in REQUIRED_KEYS:
        assert key in structured, key
        assert key in out, key

    text = " ".join(
        [
            str(out.get("executive_opinion") or ""),
            str((out.get("moat") or {}).get("assessment") or ""),
            str((out.get("capital_allocation") or {}).get("assessment") or ""),
        ]
    ).lower()
    for lazy in LAZY_PHRASES:
        assert lazy not in text
    assert "why" in " ".join(q["question"].lower() for q in out["reasoning"])
    assert "Porter Five Forces" in out["frameworks_applied"]
    assert "Business Model" in out["frameworks_applied"]
    assert out["benchmarks"]["never_self_only"] is True
    assert "reasoning" in out["confidence"]
    assert out["quality_checks"]["status"] in {"Complete", "Complete with flags"}
    assert out["ready_for_committee"] is True
    # Answers ownership question
    assert "own" in (out.get("primary_question_answer") or "").lower()


def test_hdfc_style_example_quality():
    op = analyse(
        {
            "ticker": "HDFCBANK",
            "company_analysis": {
                "company_name": "HDFC Bank",
                "business_quality": {
                    "business_quality_score": 80,
                    "revenue_drivers": ["Deposit franchise", "Retail credit"],
                    "competitive_advantages": [
                        "Distribution scale",
                        "Brand trust",
                        "Low-cost deposit franchise",
                    ],
                    "pricing_power": "Franchise pricing power in retail liabilities",
                    "brand": "High-trust retail franchise",
                    "capital_allocation": (
                        "Disciplined underwriting and conservative capital allocation historically "
                        "support returns above cost of capital"
                    ),
                    "confidence": 0.75,
                    "risks": ["Deposit competition", "Regulatory change"],
                },
            },
            "company_dossier": {
                "identity": {"company_name": "HDFC Bank", "industry": "Private banking"},
                "business_profile": {"business_model": "Universal bank franchise"},
                "management": {"governance": "Institutional-grade board oversight"},
            },
            "live_evidence": {
                "documents_used": ["Annual report commentary", "Conference call notes"],
                "freshness_score": 0.72,
            },
            "sector_intelligence": {
                "peers": ["Large private bank peers"],
                "global_peers": ["Global bank franchises"],
            },
            "finance_academy": {"applied_concepts": ["Franchise economics", "Switching costs"]},
        }
    )
    assert op.get("iai_v2") is True
    assert op["executive_opinion"]
    eo = op["executive_opinion"].lower()
    assert "own" in eo
    assert any(
        token in eo
        for token in ("deposit", "franchise", "distribution", "capital", "competitive advantage")
    )
    assert isinstance(op["moat"], dict)
    assert op["moat"].get("durability") in {"Strong", "Improving", "Medium", "Weak", "Declining"}
    assert op["business_quality"].get("grade") in {"Exceptional", "High", "Adequate", "Weak"}
    assert op["confidence"].get("reasoning") is not None
    # No valuation leakage
    blob = op["executive_opinion"].lower()
    for forbidden in ("p/e", "intrinsic", "margin of safety", "overvalued"):
        assert forbidden not in blob


def test_incomplete_assessment_when_checklist_fails():
    sparse = {
        "company": "Thin Co",
        "business_model": "",
        "advantages": [],
        "revenue_drivers": [],
        "competitive_position": "",
        "pricing_power": "",
        "brand": "",
        "capital_allocation": "",
        "growth_opportunities": [],
        "business_risks": [],
        "business_quality_score": None,
        "evidence_refs": [],
    }
    out = think(company="Thin Co", evidence=sparse, confidence={"evidence": 0.2, "knowledge": 0.2, "freshness": 0.2})
    assert out["quality_checks"]["incomplete"] is True
    assert "Incomplete Business Assessment" in (out["executive_opinion"] or "")
    assert out["ready_for_committee"] is False


def test_memory_trajectory_labels():
    put_opinion(
        "HDFCBANK",
        "business",
        {
            "summary": "Prior adequate franchise view.",
            "stance": "Neutral",
            "strengths": ["Brand trust"],
            "weaknesses": ["Competition"],
            "confidence": {"overall": 0.5},
            "business_quality": {"grade": "Adequate"},
            "moat": {"durability": "Medium"},
        },
    )
    # analyse uses slim memory; pass enriched prior via think directly
    from institutional_analysts.memory import get_previous_opinion

    prior = get_previous_opinion("HDFCBANK", "business")
    prior["business_quality"] = {"grade": "Adequate"}
    prior["moat"] = {"durability": "Medium"}
    prior["prior_growth_view"] = "Limited runway"
    out = think(
        company="HDFC Bank",
        evidence=_rich_evidence(business_quality_score=82),
        previous=prior,
        confidence={"evidence": 0.75, "knowledge": 0.75, "freshness": 0.7, "overall": 0.75},
    )
    assert out["trajectory"] in {"Improving", "Stable", "Deteriorating"}
    assert out["memory"]["trajectory"] in {"Improving", "Stable", "Deteriorating"}


def test_checklist_helper_direct():
    from institutional_analysts.business.brain.frameworks import apply_all
    from institutional_analysts.business.brain.scoring import score_dimensions

    fw = apply_all(_rich_evidence())
    sc = score_dimensions(fw, _rich_evidence())
    result = run_checklist(fw, sc)
    assert result["passed"] is True
    assert result["status"] == "Complete"
