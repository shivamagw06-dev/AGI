"""Production facade smoke tests — the surface REST routes call into."""

from __future__ import annotations

from financial_concepts import production


def test_health_reports_ok_and_no_dangling_refs():
    h = production.health()
    assert h["status"] == "ok"
    assert h["dangling_relationship_refs"] == []
    assert h["concept_count"] >= 150
    assert h["exam_question_count"] >= 150
    assert h["fabricated"] is False


def test_health_reports_all_nine_modules():
    h = production.health()
    expected = {
        "corporate_finance", "ratio_intelligence", "valuation", "banking",
        "cash_flow", "capital_allocation", "credit", "market", "business_quality",
    }
    assert expected <= set(h["modules"])


def test_dashboard_matches_health_counts():
    h = production.health()
    d = production.dashboard()
    assert d["concept_count"] == h["concept_count"]
    assert d["exam_question_count"] == h["exam_question_count"]


def test_list_concepts_all_and_by_module():
    all_c = production.list_concepts()
    assert all_c["n"] >= 150
    banking = production.list_concepts("banking")
    assert banking["n"] > 0
    assert banking["n"] < all_c["n"]
    assert "nim" in banking["concepts"]


def test_explain_facade_matches_lookup():
    result = production.explain("What is WACC?")
    assert result["found"]
    assert result["key"] == "wacc"


def test_concept_card_found_and_not_found():
    found = production.concept_card("roic")
    assert found["found"]
    assert found["title"] == "ROIC (Return on Invested Capital)"
    missing = production.concept_card("not_a_real_key")
    assert missing["found"] is False


def test_related_facade():
    r = production.related("wacc")
    assert r["found"]
    assert "cost_of_equity" in r["related"]


def test_related_unknown_key():
    r = production.related("not_a_real_key")
    assert r["found"] is False


def test_path_facade():
    r = production.path("roe_decomposition", "financial_leverage")
    assert r["found"]
    assert r["path"][0] == "roe_decomposition"


def test_graph_facade():
    g = production.graph()
    assert g["nodes"] >= 150
    assert g["isolated_concepts"] == []


def test_search_facade():
    r = production.search("enterprise value", limit=3)
    assert r["n"] > 0
    assert len(r["results"]) <= 3


def test_exam_facade_functions():
    q = production.exam_questions()
    assert q["n"] >= 150
    first_id = q["items"][0]["item_id"]
    run = production.exam_run_item(first_id)
    assert run["found"]
    grade = production.exam_grade(first_id, run["model_answer"])
    assert grade["found"]
    assert grade["passed"] is True


def test_soft_slice_for_ask_agi_enabled_and_disabled():
    hit = production.soft_slice_for_ask_agi("What is Enterprise Value?")
    assert hit["enabled"] is True
    assert hit["financial_concepts"]["key"] == "enterprise_value"

    miss = production.soft_slice_for_ask_agi("what is the weather today")
    assert miss["enabled"] is False
