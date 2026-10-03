from finance_research_skill.production import compile_evidence_contract
from finance_research_skill.evidence_tagger import tag_evidence


def test_company_contract_is_typed_and_strips_sensitive_fields():
    result = compile_evidence_contract(
        entity="ICICIBANK",
        request_id="req-1",
        research_intelligence={
            "matched": True,
            "intent": "forecast",
            "sections": {
                "FORECAST": {"horizon": "5d", "expected_alpha": 0.9, "token": "nope"},
                "DATA_QUALITY": {"evidence_complete": True, "missing_components": []},
            },
        },
        semantic_research={"query": "private question", "SOURCES": []},
    )
    assert result["route"] == "COMPANY_RESEARCH"
    assert result["company_required"] is True
    assert result["answerability"] == "SUFFICIENT"
    assert result["forecasts"]["expected_alpha"] == 0.9
    assert "token" not in result["forecasts"]
    assert "query" not in result
    assert result["privacy"]["filesystem_access"] is False


def test_house_research_does_not_require_company():
    result = compile_evidence_contract(
        entity=None,
        research_intelligence={},
        semantic_research={
            "source_hierarchy": ["AGI_PROPRIETARY_RESEARCH"],
            "answerability": {"status": "SUFFICIENT"},
            "AGI_HOUSE_VIEW": {"documents": [{"document_id": "doc-1", "title": "AI Monitor"}]},
            "SOURCES": [{"document_id": "doc-1", "title": "AI Monitor"}],
        },
    )
    assert result["route"] == "HOUSE_RESEARCH"
    assert result["company_required"] is False
    assert result["answerability"] == "SUFFICIENT"
    assert result["house_research"][0]["document_id"] == "doc-1"


def test_weak_thematic_retrieval_fails_closed():
    result = compile_evidence_contract(
        entity=None,
        research_intelligence={},
        semantic_research={"answerability": {"status": "INSUFFICIENT"}},
    )
    assert result["route"] == "THEMATIC_RESEARCH"
    assert result["answerability"] == "INSUFFICIENT"
    assert "relevant_evidence" in result["missing_components"]


def test_financial_taxonomy_tags_direction_dimension_horizon_and_catalyst():
    result = tag_evidence(
        evidence_id="ev-1",
        entity="TCS",
        source="company_filing",
        text=(
            "Management raised revenue guidance for the next quarter after strong demand "
            "and a significant contract win."
        ),
    )
    assert result["direction"] == "positive"
    assert "revenue" in result["dimensions"]
    assert "guidance" in result["dimensions"]
    assert result["guidance_direction"] == "positive"
    assert result["magnitude"] == "high"
    assert result["horizon"] == "1_2_quarters"
    assert "contract" in result["catalyst_cues"]
    assert result["recommendation_generated"] is False


def test_contract_includes_tags_for_approved_house_research_only():
    result = compile_evidence_contract(
        entity=None,
        research_intelligence={},
        semantic_research={
            "answerability": {"status": "SUFFICIENT"},
            "AGI_HOUSE_VIEW": {
                "documents": [
                    {
                        "document_id": "doc-1",
                        "document_type": "agi_research",
                        "title": "AI capex accelerates",
                        "snippet": "Strong data-centre investment benefits power demand over the long term.",
                    }
                ]
            },
        },
    )
    assert result["evidence_tags"][0]["evidence_id"] == "doc-1"
    assert result["evidence_tags"][0]["direction"] == "positive"
    assert result["evidence_tags"][0]["horizon"] == "long_term"
