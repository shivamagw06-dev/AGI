from app.ui.executive_composer import alias_tickers_from_question
from app.ui.executive_composer import compose_executive, is_planning_scaffold
from app.ui.ticker_guard import alias_ticker_from_question
from app.ui.service import _is_consensus_fact_question


def test_core_company_names_bind_to_canonical_tickers():
    expected = {
        "Explain Axis Bank": "AXISBANK",
        "What does Oil and Natural Gas Corporation do?": "ONGC",
        "Brief me on Sun Pharmaceutical Industries": "SUNPHARMA",
        "UltraTech Cement investment thesis": "ULTRACEMCO",
        "Power Grid Corporation of India risks": "POWERGRID",
        "Avenue Supermarts business model": "DMART",
    }
    for question, ticker in expected.items():
        assert alias_ticker_from_question(question) == ticker


def test_comparison_binding_preserves_mention_order():
    assert alias_tickers_from_question("Compare NTPC with Power Grid")[:2] == [
        "NTPC",
        "POWERGRID",
    ]


def test_ambiguous_group_stems_do_not_bind():
    assert alias_ticker_from_question("What is HDFC?") is None
    assert alias_ticker_from_question("What sector is Tata in?") is None


def test_internal_framework_procedure_is_never_a_user_answer():
    assert is_planning_scaffold(
        "Framework-selection confidence: High (99%) Procedure: Map drivers → conclusion"
    )
    assert is_planning_scaffold("Required domains present or softened. □ Check margins")


def test_composer_rejects_wrong_company_and_uses_company_pack():
    out = compose_executive(
        "Give me a full institutional view on Axis Bank",
        detected_ticker="AXISBANK",
        candidates=["Evidence: INFY company intelligence. Decision policy lens: quality."],
        packs={
            "company_analysis": {
                "executive_summary": "Axis Bank is a diversified private bank with a 58/100 business-quality score.",
                "business_overview": "Axis Bank operates a deposit-funded lending and fee-income franchise.",
            }
        },
    )
    assert "Axis Bank" in out["executive"]
    assert "INFY" not in out["executive"]


def test_consensus_fact_queries_take_the_database_fact_route():
    assert _is_consensus_fact_question("What is the consensus target price for Infosys?")
    assert _is_consensus_fact_question("What upside does the street see in HDFC Bank?")
    assert _is_consensus_fact_question("What is the high target for Infosys?")
    assert not _is_consensus_fact_question("Give me a full valuation of Infosys")


def test_consensus_database_answer_includes_structured_answer_pack():
    from app.ui.service import UiService

    view = UiService().search("What is the consensus target price for Infosys?")
    payload = view.model_dump(mode="json")

    assert "consensus target" in payload["executive_summary"].lower()
    pack = payload["answer"]["answer_pack"]
    assert pack["direct_answer"] == payload["executive_summary"]
    assert pack["company"]["ticker"] == "INFY"
    assert pack["governance"]["quality_gates"]["exact_fact"] is True
    assert pack["governance"]["execution_advice"] is False
