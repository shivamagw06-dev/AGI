"""KUL core — registry, planners, fusion, CapIQ field unlock."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("IKT_STORE_ROOT", str(ROOT / "data" / "institutional_knowledge_tables"))


def test_registry_lists_all_expected_providers():
    from knowledge_unification.registry import KnowledgeRegistry

    reg = KnowledgeRegistry()
    ids = {p.spec.id for p in reg.all()}
    for required in (
        "research_intelligence",
        "portfolio_intelligence",
        "investment_intelligence",
        "industry_intelligence",
        "business_intelligence",
        "valuation_consensus",
        "capiq_ikt",
        "ikl",
        "company_memory",
        "knowledge_factory",
        "cgl",
        "financial_concepts",
        "financial_foundations",
        "financial_statement_intelligence",
        "academy",
        "legacy_kip",
    ):
        assert required in ids


def test_query_planner_types_concept_and_company():
    from knowledge_unification.query_planner import plan_query

    c = plan_query("Explain enterprise value")
    assert "concept" in c.question_types or "valuation" in c.question_types
    assert c.requires_deterministic_finance or "concept" in c.question_types

    co = plan_query("What is HDFC Bank's business model?")
    assert "company" in co.question_types or co.ticker_hint == "HDFCBANK"


def test_knowledge_plan_orders_memory_before_legacy_for_company():
    from knowledge_unification.knowledge_planner import build_knowledge_plan
    from knowledge_unification.query_planner import plan_query
    from knowledge_unification.registry import KnowledgeRegistry

    q = plan_query("What is Reliance Industries' business model?")
    if not q.ticker_hint:
        q.ticker_hint = "RELIANCE"
        q.question_types = ["company", "business_model"]
    plan = build_knowledge_plan(q, registry=KnowledgeRegistry())
    assert "business_intelligence" in plan.provider_ids
    assert "capiq_ikt" in plan.provider_ids or "company_memory" in plan.provider_ids
    assert plan.provider_ids.index("business_intelligence") < plan.provider_ids.index("legacy_kip")
    if "legacy_kip" in plan.provider_ids and "capiq_ikt" in plan.provider_ids:
        assert plan.provider_ids.index("capiq_ikt") < plan.provider_ids.index("legacy_kip")


def test_concept_plan_excludes_legacy_retrieval_as_default():
    from knowledge_unification.knowledge_planner import build_knowledge_plan
    from knowledge_unification.query_planner import plan_query
    from knowledge_unification.registry import KnowledgeRegistry

    q = plan_query("Explain ROIC")
    plan = build_knowledge_plan(q, registry=KnowledgeRegistry())
    assert "financial_concepts" in plan.provider_ids
    # legacy may still appear for unknown intents, but not for pure concept
    assert plan.provider_ids[0] in {
        "financial_concepts",
        "financial_foundations",
        "financial_statement_intelligence",
        "academy",
    }


def test_plan_and_gather_company_fuses_capiq_when_seeded():
    from knowledge_unification.production import plan_and_gather
    from institutional_knowledge_tables.store import list_companies

    if len(list_companies()) < 100:
        return  # skip if local store not seeded
    out = plan_and_gather("What is HDFC Bank's business model?")
    assert out["ok"] is True
    assert out["answerable"] is True
    sources = out["coverage"]["knowledge_sources_used"]
    assert "business_intelligence" in sources
    assert "capiq_ikt" in sources or "company_memory" in sources
    # CapIQ previously-unused fields should appear in company intelligence / facts
    market = (out.get("company_intelligence") or {}).get("market") or {}
    assert (
        market.get("market_cap") is not None
        or (out.get("company_intelligence") or {}).get("business")
        or any(
            f.get("field", "").startswith("returns_")
            for r in out.get("provider_results") or []
            if r.get("provider_id") == "capiq_ikt"
            for f in r.get("facts") or []
        )
    )


def test_business_question_routes_bi_before_legacy():
    from knowledge_unification.knowledge_planner import build_knowledge_plan
    from knowledge_unification.query_planner import plan_query
    from knowledge_unification.registry import KnowledgeRegistry

    q = plan_query("What is TCS's competitive advantage?")
    plan = build_knowledge_plan(q, registry=KnowledgeRegistry())
    assert "moat" in q.question_types or "business_model" in q.question_types
    assert "business_intelligence" in plan.provider_ids
    assert plan.provider_ids[0] == "business_intelligence"
    assert "industry_intelligence" in plan.provider_ids
    assert plan.provider_ids.index("business_intelligence") < plan.provider_ids.index(
        "industry_intelligence"
    )
    assert "legacy_kip" not in plan.provider_ids or plan.provider_ids.index(
        "business_intelligence"
    ) < plan.provider_ids.index("legacy_kip")


def test_industry_question_routes_ii_before_bi():
    from knowledge_unification.knowledge_planner import build_knowledge_plan
    from knowledge_unification.query_planner import plan_query
    from knowledge_unification.registry import KnowledgeRegistry

    q = plan_query("Why do banks use P/B?")
    plan = build_knowledge_plan(q, registry=KnowledgeRegistry())
    assert "industry_intelligence" in plan.provider_ids
    assert plan.provider_ids[0] == "industry_intelligence"
    assert "business_intelligence" in plan.provider_ids
    assert plan.provider_ids.index("industry_intelligence") < plan.provider_ids.index(
        "business_intelligence"
    )


def test_investment_question_routes_inv_before_bi():
    from knowledge_unification.knowledge_planner import build_knowledge_plan
    from knowledge_unification.query_planner import plan_query
    from knowledge_unification.registry import KnowledgeRegistry

    q = plan_query("Evaluate Reliance's investment quality.")
    plan = build_knowledge_plan(q, registry=KnowledgeRegistry())
    assert "investment" in q.question_types
    assert "investment_intelligence" in plan.provider_ids
    assert plan.provider_ids[0] == "investment_intelligence"
    assert plan.provider_ids.index("investment_intelligence") < plan.provider_ids.index(
        "business_intelligence"
    )
    assert plan.provider_ids.index("investment_intelligence") < plan.provider_ids.index(
        "industry_intelligence"
    )


def test_research_question_routes_ri_first():
    from knowledge_unification.knowledge_planner import build_knowledge_plan
    from knowledge_unification.query_planner import plan_query
    from knowledge_unification.registry import KnowledgeRegistry

    q = plan_query("Explain Reliance's business segments from the annual report.")
    plan = build_knowledge_plan(q, registry=KnowledgeRegistry())
    assert "research" in q.question_types
    assert plan.provider_ids[0] == "research_intelligence_engine"
    assert "research_intelligence" in plan.provider_ids


def test_portfolio_question_routes_pi_first():
    from knowledge_unification.knowledge_planner import build_knowledge_plan
    from knowledge_unification.query_planner import plan_query
    from knowledge_unification.registry import KnowledgeRegistry

    q = plan_query("Explain portfolio construction for AGIB Core India Equity.")
    plan = build_knowledge_plan(q, registry=KnowledgeRegistry())
    assert "portfolio" in q.question_types
    assert plan.provider_ids[0] == "portfolio_intelligence"


def test_plan_and_gather_concept_uses_deterministic_engine():
    from knowledge_unification.production import plan_and_gather

    out = plan_and_gather("Explain enterprise value")
    assert out["answerable"] is True
    sources = out["coverage"]["knowledge_sources_used"]
    assert any(
        s in sources
        for s in (
            "financial_concepts",
            "financial_foundations",
            "financial_statement_intelligence",
        )
    )
    assert "legacy_kip" not in sources or sources.index("legacy_kip") > 0


def test_answer_for_ask_returns_compact_payload():
    from knowledge_unification.production import answer_for_ask

    hit = answer_for_ask("Explain EBITDA")
    assert hit is not None
    assert hit["engine"] in {"knowledge_unification", "universal_knowledge"}
    assert hit["summary"]
    assert hit.get("providers_used") or hit.get("modules_used") or hit.get("coverage")


def test_ranking_rejects_empty_and_duplicates():
    from knowledge_unification.ranking import rank_and_filter
    from knowledge_unification.schema import ProviderResult

    results = [
        ProviderResult("a", True, True, 1, 0.0, rejected_reason="empty"),
        ProviderResult("b", True, False, 2, 0.8, summary="Same text", why=["x"]),
        ProviderResult("c", True, False, 3, 0.7, summary="Same text", why=["y"]),
        ProviderResult("d", False, True, 4, 0.0, error="boom"),
    ]
    kept = rank_and_filter(results)
    assert len(kept) == 1
    assert kept[0].provider_id == "b"
