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


def test_missing_consensus_is_honest_and_never_falls_back_to_profile(monkeypatch):
    import knowledge_unification.production as production

    monkeypatch.setattr(
        production,
        "plan_and_gather",
        lambda *_args, **_kwargs: {
            "answerable": True,
            "summary": "Generic company profile",
            "coverage": {"knowledge_sources_used": ["business_intelligence"]},
        },
    )

    result = production.answer_for_ask(
        "What is the consensus target price for Axis Bank?",
        ticker="AXISBANK",
    )

    assert result is not None
    assert result["insufficient_evidence"] is True
    assert "No Capital IQ market-consensus record" in result["summary"]
    assert "invent a target price" in result["summary"]
    assert "Generic company profile" not in result["summary"]


def test_company_lookup_does_not_use_market_screen_when_row_is_missing(monkeypatch):
    import valuation_consensus.store as store

    monkeypatch.setattr(store, "get_row", lambda _ticker: None)
    result = answer_for_ask(
        "What is the consensus target price for Axis Bank?",
        ticker="AXISBANK",
    )

    assert result is not None
    assert result["insufficient_evidence"] is True
    assert "No Capital IQ market-consensus record" in result["summary"]
