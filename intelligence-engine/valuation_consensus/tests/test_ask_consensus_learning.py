"""Ask AGI learns Capital IQ consensus — routing, answers, and guardrails."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture()
def seeded_store(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        monkeypatch.setenv("VALUATION_CONSENSUS_ROOT", td)
        from valuation_consensus import store

        store.invalidate_cache()
        store.publish_rows(
            {
                "INFY": {
                    "ticker": "INFY",
                    "company_name": "Infosys Limited",
                    "cmp": 979.0,
                    "target_price": 1039.75,
                    "target_high": 1300.0,
                    "target_low": 800.0,
                    "upside": 6.1,
                    "buy_count": 18,
                    "outperform_count": 6,
                    "hold_count": 12,
                    "sell_count": 4,
                    "coverage": 42,
                    "sector": "Information Technology",
                    "industry": "IT Consulting and Other Services",
                },
                "TCS": {
                    "ticker": "TCS",
                    "company_name": "Tata Consultancy Services Limited",
                    "cmp": 2055.0,
                    "target_price": 2155.81,
                    "upside": 4.88,
                    "buy_count": 14,
                    "hold_count": 20,
                    "sell_count": 6,
                    "coverage": 40,
                    "sector": "Information Technology",
                    "industry": "IT Consulting and Other Services",
                },
                "ALLCARGO": {
                    "ticker": "ALLCARGO",
                    "company_name": "Allcargo Logistics Limited",
                    "cmp": 30.0,
                    "target_price": 149.0,
                    "upside": 398.1,
                    "buy_count": 2,
                    "coverage": 3,
                    "sector": "Industrials",
                    "industry": "Air Freight and Logistics",
                },
            },
            source_file="unit.xlsx",
            imported_by="test",
        )
        yield
        store.invalidate_cache()


def test_query_planner_types_consensus_questions():
    from knowledge_unification.query_planner import plan_query

    for q in (
        "What is the consensus target price for Infosys?",
        "How many analysts cover TCS?",
        "What is the analyst rating split for Reliance Industries?",
        "Which companies have the highest consensus upside?",
    ):
        assert "consensus" in plan_query(q).question_types, q


def test_knowledge_plan_leads_with_valuation_consensus(seeded_store):
    from knowledge_unification.knowledge_planner import build_knowledge_plan
    from knowledge_unification.query_planner import plan_query
    from knowledge_unification.registry import KnowledgeRegistry

    q = plan_query("What is the consensus target price for Infosys?")
    q.ticker_hint = q.ticker_hint or "INFY"
    plan = build_knowledge_plan(q, registry=KnowledgeRegistry())
    assert plan.provider_ids[0] == "valuation_consensus"


def test_ask_answers_company_consensus_from_store(seeded_store):
    from knowledge_unification.production import plan_and_gather

    out = plan_and_gather("What is the consensus target price for Infosys?", ticker="INFY")
    assert out.get("answerable")
    sources = (out.get("coverage") or {}).get("knowledge_sources_used") or []
    assert "valuation_consensus" in sources
    summary = out.get("summary") or ""
    assert "1,039" in summary or "1039" in summary
    assert "consensus" in summary.lower()


def test_ask_answers_market_wide_consensus_screen(seeded_store):
    from knowledge_unification.production import plan_and_gather

    out = plan_and_gather("Which companies have the highest consensus upside?")
    sources = (out.get("coverage") or {}).get("knowledge_sources_used") or []
    assert "valuation_consensus" in sources
    assert "ALLCARGO" in (out.get("summary") or "")


def test_entity_intelligence_allows_consensus_screens():
    from entity_intelligence.resolve import resolve

    for q in (
        "Which companies have the highest consensus upside?",
        "Which stocks have the most analyst coverage?",
    ):
        out = resolve(q)
        assert out.get("allow_planner") is True, q
        assert out.get("ticker") is None


def test_entity_contract_still_blocks_wrong_entity():
    from entity_intelligence.resolve import resolve

    air = resolve("What is the consensus target price for Air India?")
    assert air.get("ticker") != "BHARTIARTL"

    unknown = resolve("What is the consensus target for Quorvex Analytics Private Limited?")
    assert unknown.get("state") == "unsupported_entity"


def test_consensus_never_presented_as_agi_recommendation(seeded_store):
    from knowledge_unification.providers.valuation_consensus import ValuationConsensusProvider
    from knowledge_unification.schema import QueryPlan

    provider = ValuationConsensusProvider()
    plan = QueryPlan(
        question="What is the analyst rating split for Infosys?",
        question_types=["consensus", "company"],
        ticker_hint="INFY",
        requires_company=True,
    )
    result = provider.consult(plan)
    blob = (result.summary + " " + " ".join(result.why)).lower()
    assert "market consensus" in blob
    assert "not an agi recommendation" in blob or "not agi advice" in blob
    # AGI must not say buy/sell itself — broker counts stay labelled as counts.
    assert "we recommend" not in blob
    assert "you should buy" not in blob
