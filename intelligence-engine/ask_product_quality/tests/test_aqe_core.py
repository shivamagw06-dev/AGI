"""AQE v1.0 unit tests — routing, pedagogy, confidence, quality gate."""

from __future__ import annotations


def test_health():
    from ask_product_quality.production import health

    h = health()
    assert h["ok"] is True
    assert "9.2" in h["programme"]


def test_macro_concepts_route_to_concepts():
    from knowledge_unification.query_planner import plan_query

    for q in (
        "What is equity risk premium?",
        "Explain country risk premium",
        "What is inflation?",
    ):
        plan = plan_query(q)
        assert "concept" in plan.question_types
        assert "macro" not in plan.question_types


def test_costco_moat_allows_bi_pedagogy():
    from entity_intelligence.production import analyse, should_short_circuit
    from knowledge_unification.production import plan_and_gather

    contract = analyse("What is Costco's moat?")
    assert contract.get("allow_planner") is True
    assert contract.get("ticker") is None
    assert should_short_circuit(contract) is False

    payload = plan_and_gather("What is Costco's moat?")
    sources = list((payload.get("coverage") or {}).get("knowledge_sources_used") or [])
    consulted = list((payload.get("diagnostics") or {}).get("providers_consulted") or [])
    plan_ids = list(((payload.get("diagnostics") or {}).get("plan") or {}).get("provider_ids") or [])
    assert "business_intelligence" in sources or "business_intelligence" in consulted or "business_intelligence" in plan_ids
    # Never CapIQ-bind an Indian name for Costco.
    ticker = ((payload.get("company_intelligence") or {}).get("identity") or {}).get("ticker")
    assert not ticker or str(ticker).upper() not in {"RELIANCE", "TCS", "INFY", "HDFCBANK"}


def test_compare_menu_includes_bi_and_capiq_early():
    from knowledge_unification.knowledge_planner import build_knowledge_plan
    from knowledge_unification.query_planner import plan_query

    plan = build_knowledge_plan(plan_query("Compare Infosys vs TCS."))
    ids = list(plan.provider_ids)
    assert "business_intelligence" in ids
    assert "capiq_ikt" in ids
    assert ids.index("business_intelligence") < ids.index("research_intelligence_engine")
    assert ids.index("capiq_ikt") < 8


def test_metadata_sector_route():
    from company_identity.metadata_router import route

    hit = route("Axis Bank primary sector")
    assert hit is not None
    assert hit.get("route") == "company_metadata"
    assert hit.get("ticker")


def test_quality_gate_rejects_boilerplate():
    from ask_product_quality.production import quality_gate

    bad = quality_gate(
        {
            "summary": "Based on retrieved evidence for the subject: Indian Stock Market Q&A",
            "coverage": {"knowledge_sources_used": ["legacy_kip"]},
            "confidence": 80,
        },
        question="Why does Visa generate high free cash flow?",
    )
    assert bad["hard_fail"] is True
    assert "unsupported_conclusion_or_boilerplate" in bad["issues"]


def test_confidence_never_defaults_arbitrarily():
    from ask_product_quality.confidence import calibrate

    empty = calibrate()
    assert empty["overall_confidence"] is None
    assert empty["level"] == "Unknown"

    scored = calibrate(overall=0.8, evidence_count=4, entity_confidence=0.95)
    assert scored["overall_confidence"] is not None
    assert scored["level"] in {"High", "Medium", "Low"}


def test_routing_dashboard():
    from ask_product_quality.production import dashboard

    board = dashboard()
    assert board["ok"] is True
    assert board["routing"]["total"] >= 5
    assert "targets" in board


def test_titan_sector_keeps_company_bind():
    from knowledge_unification.query_planner import plan_query
    from knowledge_unification.production import plan_and_gather

    plan = plan_query("What sector is Titan Company in?")
    assert plan.ticker_hint == "TITAN"
    out = plan_and_gather("What sector is Titan Company in?")
    sources = list((out.get("coverage") or {}).get("knowledge_sources_used") or [])
    assert "capiq_ikt" in sources
