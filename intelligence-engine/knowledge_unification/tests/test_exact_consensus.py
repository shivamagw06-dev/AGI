from knowledge_unification.production import answer_for_ask


def test_exact_consensus_question_is_not_overwritten_by_company_profile():
    result = answer_for_ask("What is the consensus target price for Infosys?", ticker="INFY")

    assert result is not None
    assert result.get("exact_fact") is True
    assert "valuation_consensus" in result.get("providers_used", [])
    assert "consensus target" in result.get("summary", "").lower()
    assert "1,039.75" in result.get("summary", "")
    assert "consulting, technology" not in result.get("summary", "").lower()


def test_high_target_question_leads_with_high_target():
    result = answer_for_ask("What is the high target for Infosys?", ticker="INFY")

    assert result is not None
    assert "high target" in result["summary"].lower()
    assert "1,398.42" in result["summary"]
