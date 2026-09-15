"""Institutional Investor Curriculum v1.0 tests."""

from __future__ import annotations

from institutional_investor_curriculum import (
    ANCHOR_COMPANIES,
    EDITORIAL_BENCHMARKS,
    TARGET_BENCHMARK_COUNT,
    UNIVERSAL_QUESTIONS,
    curriculum_summary,
    editorial_process,
    get_benchmark,
    get_domain,
    hall_of_fame_benchmark_ids,
    list_benchmarks,
    list_domains,
    list_universal_questions,
)


def test_curriculum_structure():
    summary = curriculum_summary()
    assert summary["universal_questions"] == 100
    assert summary["anchor_companies"] == 10
    assert summary["editorial_benchmarks"] == 1000
    assert len(UNIVERSAL_QUESTIONS) == 100
    assert len(EDITORIAL_BENCHMARKS) == TARGET_BENCHMARK_COUNT


def test_ten_domains_ten_questions_each():
    domains = list_domains()
    assert len(domains) == 10
    for d in domains:
        assert len(d["universal_question_ids"]) == 10


def test_universal_questions_not_company_specific():
    q = list_universal_questions(domain="idea_generation")[0]
    assert q["company_specific"] is False
    assert "{company}" in q["template"]


def test_benchmarks_instantiate_for_all_anchors():
    for ticker, _ in ANCHOR_COMPANIES:
        company_benchmarks = list_benchmarks(ticker=ticker)
        assert len(company_benchmarks) == 100


def test_benchmark_ids_and_tcs_hall_of_fame():
    assert EDITORIAL_BENCHMARKS[0]["id"] == "IIC_0001"
    assert EDITORIAL_BENCHMARKS[0]["ticker"] == "TCS"
    assert EDITORIAL_BENCHMARKS[0]["question"] == "Does Tata Consultancy Services deserve research today?"
    hof = hall_of_fame_benchmark_ids()
    assert len(hof) == 100
    assert all(get_benchmark(bid)["ticker"] == "TCS" for bid in hof)


def test_domain_retrieval():
    domain = get_domain("valuation")
    assert domain["title"] == "Valuation"
    assert len(domain["universal_questions"]) == 10
    assert domain["editorial_objective"] == "Teach expectations, not multiples."


def test_editorial_process():
    process = editorial_process()
    assert process["cadence"] == "weekly"
    assert len(process["steps"]) == 6
    assert process["architecture_changes"] is False
