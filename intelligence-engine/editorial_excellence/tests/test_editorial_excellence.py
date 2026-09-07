"""Editorial Excellence Program v1.0 tests."""

from __future__ import annotations

from editorial_excellence import (
    apply_editorial_excellence,
    health,
    list_rules,
    quality_gates,
    rule_count,
    score_editorial,
)
from editorial_excellence.schema import PROGRAM_VERSION, TARGET_BENCHMARK_COUNT
from editorial_excellence.reports import monthly_report, weekly_review
from institutional_writing_benchmark import (
    get_benchmark,
    hall_of_fame_ids,
    list_benchmarks,
    list_domains,
    load_hall_of_fame,
)
from institutional_writing_benchmark.registry import BENCHMARK_QUESTIONS
from institutional_writing_constitution import apply_institutional_writing_constitution


def test_health():
    h = health()
    assert h["status"] == "ok"
    assert h["version"] == PROGRAM_VERSION
    assert h["benchmark_questions"] == TARGET_BENCHMARK_COUNT
    assert h["benchmark_target"] == 1000
    assert h["editorial_rules"] == rule_count()


def test_benchmark_registry_has_1000_questions():
    assert len(BENCHMARK_QUESTIONS) == 1000
    ids = [q["id"] for q in BENCHMARK_QUESTIONS]
    assert len(set(ids)) == 1000


def test_ten_decision_domains():
    domains = list_domains()
    assert len(domains) == 10
    valuation = list_benchmarks(domain="valuation", ticker="TCS", limit=20)
    assert len(valuation) == 10
    assert get_benchmark("IIC_0001")["domain"] == "idea_generation"


def test_hall_of_fame_is_tcs_universal_curriculum():
    ids = hall_of_fame_ids()
    assert len(ids) == 100
    assert all(get_benchmark(i)["ticker"] == "TCS" for i in ids)


def test_editorial_principles_in_rules():
    rules = list_rules(category="principles")
    assert len(rules) == 6


def test_score_editorial_curriculum_dimensions():
    pack = apply_institutional_writing_constitution(
        {"ticker": "TCS", "company": "Tata Consultancy Services", "query": "Does TCS deserve research today?"},
        query="Does TCS deserve research today?",
    )
    editorial = score_editorial(pack)
    for dim in (
        "clarity",
        "business_understanding",
        "investment_insight",
        "portfolio_relevance",
        "overall_editorial_score",
    ):
        assert dim in editorial["scorecard"]


def test_apply_editorial_excellence_wiring():
    base = apply_institutional_writing_constitution(
        {"ticker": "TCS", "company": "TCS", "query": "Does TCS deserve research today?"},
        query="Does TCS deserve research today?",
    )
    out = apply_editorial_excellence(base, query="Does TCS deserve research today?", benchmark_id="IIC_0001")
    ee = out["editorial_excellence"]
    assert ee["enabled"] is True
    assert out.get("editorial_score") is not None


def test_hall_of_fame_keeps_better_version():
    from institutional_writing_benchmark.hall_of_fame import compare_and_maybe_update

    bench_id = "IIC_HOF_TEST"
    compare_and_maybe_update(
        bench_id,
        question="Test question",
        response_text="The central investment debate centers on durability.",
        editorial_score=85.0,
        forward_rating="MINOR_EDITS",
    )
    result = compare_and_maybe_update(
        bench_id,
        question="Test question",
        response_text="Improved response with because and depends on clarity.",
        editorial_score=92.0,
        forward_rating="YES",
    )
    assert result["improved"] is True
    hof = load_hall_of_fame()
    assert hof["entries"][bench_id]["editorial_score"] == 92.0


def test_weekly_and_monthly_reports():
    sample = [
        {"overall_editorial_score": 88, "forward_without_editing": "MINOR_EDITS", "writing_problems": ["weak_conclusion"]},
        {"overall_editorial_score": 95, "forward_without_editing": "YES", "writing_problems": []},
    ]
    weekly = weekly_review(sample)
    assert weekly["sample_size"] == 2
    monthly = monthly_report(sample)
    assert monthly["forward_without_editing_yes_pct"] == 50.0
