from unittest.mock import patch

import pytest

from entity_intelligence.production import analyse
from entity_intelligence.schema import STATE_VERIFIED_CONCEPT, STATE_VERIFIED_ENTITY
from semantic_research_retrieval.routing import (
    COMPANY_RESEARCH,
    HOUSE_RESEARCH,
    THEMATIC_RESEARCH,
    classify_research_route,
    initial_research_trace,
    record_answer_synthesis,
    record_semantic_retrieval,
)


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("What does AGI think AI spending means for sector rotation?", HOUSE_RESEARCH),
        ("Could hyperscaler capex benefit power and industrial names?", THEMATIC_RESEARCH),
        ("How do policy shifts interact with AI investment?", THEMATIC_RESEARCH),
        ("Which sectors may gain if data-center investment stays elevated?", THEMATIC_RESEARCH),
        ("What was AGI's house view in the Global Investment Monitor?", HOUSE_RESEARCH),
        ("AGI Greenpac valuation", COMPANY_RESEARCH),
        ("AGI Infra fundamentals", COMPANY_RESEARCH),
    ],
)
def test_acceptance_routes_are_immutable(question, expected):
    assert classify_research_route(question) == expected


@pytest.mark.parametrize(
    "question",
    [
        "What does AGI think AI spending means for sector rotation?",
        "Could hyperscaler capex benefit power and industrial names?",
        "How do policy shifts interact with AI investment?",
        "Which sectors may gain if data-center investment stays elevated?",
        "What was AGI's house view in the Global Investment Monitor?",
    ],
)
def test_house_and_thematic_questions_bypass_company_resolution(question):
    result = analyse(question)
    assert result["state"] == STATE_VERIFIED_CONCEPT
    assert result["allow_planner"] is True
    assert result["ticker"] is None
    assert result["research_route"] in {HOUSE_RESEARCH, THEMATIC_RESEARCH}


@pytest.mark.parametrize(
    ("question", "ticker"),
    [("AGI Greenpac valuation", "AGI"), ("AGI Infra fundamentals", "AGIIL")],
)
def test_listed_agi_companies_keep_strict_entity_resolution(question, ticker):
    with patch(
        "entity_intelligence.resolve._canonical_capiq_ticker", return_value=ticker
    ), patch(
        "entity_intelligence.resolve._canonical_identity",
        return_value={"company_name": question.rsplit(" ", 1)[0]},
    ):
        result = analyse(question)
    assert result["state"] == STATE_VERIFIED_ENTITY
    assert result["allow_planner"] is True
    assert result["ticker"] == ticker


def test_research_trace_exposes_each_acceptance_stage():
    trace = initial_research_trace(
        "Which sectors may gain if data-center investment stays elevated?"
    )
    trace = record_semantic_retrieval(
        trace,
        {
            "enabled": True,
            "AGI_HOUSE_VIEW": {
                "documents": [
                    {
                        "document_id": "doc_b3733303faa7",
                        "title": "Global Investment Monitor: AI Capital, Policy Shifts and the Next Market Rotation",
                        "retrieval_score": 0.71,
                    }
                ]
            },
            "answerability": {"status": "SUFFICIENT"},
        },
    )
    trace = record_answer_synthesis(trace, completed=True)
    assert trace == {
        "query": "Which sectors may gain if data-center investment stays elevated?",
        "route": THEMATIC_RESEARCH,
        "company_required": False,
        "semantic_retrieval": "EXECUTED",
        "matched_documents": [
            {
                "document_id": "doc_b3733303faa7",
                "title": "Global Investment Monitor: AI Capital, Policy Shifts and the Next Market Rotation",
                "score": 0.71,
            }
        ],
        "global_investment_monitor": "MATCH",
        "answerability": "SUFFICIENT",
        "answer_synthesis": "EXECUTED",
        "failure_stage": None,
    }


def test_research_trace_labels_evidence_insufficiency():
    trace = record_semantic_retrieval(
        initial_research_trace("Could hyperscaler capex benefit power names?"),
        {
            "enabled": True,
            "AGI_HOUSE_VIEW": {"documents": [{"title": "Weak thematic match"}]},
            "answerability": {"status": "INSUFFICIENT"},
        },
    )
    assert trace["failure_stage"] == "EVIDENCE_INSUFFICIENCY"
