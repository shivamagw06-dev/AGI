from answer_packs.builder import build_answer_pack


def test_answer_pack_preserves_company_database_fields_and_governance():
    pack = build_answer_pack(
        question="Brief me on Axis Bank",
        ticker="AXISBANK",
        executive="Axis Bank is a deposit-funded private bank.",
        confidence=64,
        company_analysis={
            "identity": {"company_name": "Axis Bank", "sector": "Banking"},
            "business_overview": "A lending and fee-income franchise.",
            "business_quality": {"business_quality_score": 58, "grade": "C"},
            "financial_intelligence": {
                "narrative": "Monitor NIM, credit cost and deposits.",
                "what_deserves_monitoring": ["NIM", "credit cost"],
            },
            "recommendation_readiness": {"overall": 35, "gate": "Recommendation Withheld"},
        },
        evidence_used=[{"title": "FY2026 annual report", "source": "company filing"}],
        quality_gates={"financials_supported": True},
    )
    assert pack["company"]["ticker"] == "AXISBANK"
    assert pack["business"]["quality_score"] == 58
    assert pack["financials"]["monitor"] == ["NIM", "credit cost"]
    assert pack["evidence"][0]["source"] == "company filing"
    assert pack["governance"]["execution_advice"] is False
