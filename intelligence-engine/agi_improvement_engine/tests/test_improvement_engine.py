from __future__ import annotations

import asyncio
import json

import pytest

from agi_improvement_engine.questions import generate_questions
from agi_improvement_engine.evaluator import _public_citations
from agi_improvement_engine.scoring import score_evaluation
from agi_improvement_engine.store import append_jsonl
from agi_improvement_engine.worker import run_session


def test_question_generation_is_diversified_and_deterministic():
    left = generate_questions(100, seed=42)
    right = generate_questions(100, seed=42)
    assert left == right
    assert len({q["ticker"] for q in left}) >= 30
    assert len({q["sector"] for q in left}) >= 25
    assert len({q["difficulty"] for q in left}) == 5
    assert max(sum(1 for q in left if q["ticker"] == ticker) for ticker in {q["ticker"] for q in left}) <= 4


def test_critical_failure_forces_zero_even_with_high_dimensions():
    scored = score_evaluation({
        "dimensions": {name: 100 for name in (
            "entity_correctness", "numerical_accuracy", "evidence_support",
            "financial_reasoning", "freshness", "completeness", "communication",
        )},
        "critical_failures": ["invented_number"],
        "root_causes": ["UNSUPPORTED_CLAIM", "NOT_A_REAL_LABEL"],
    })
    assert scored["pre_critical_score"] == 100
    assert scored["score"] == 0
    assert scored["passed"] is False
    assert scored["root_causes"] == ["UNSUPPORTED_CLAIM"]


def test_dry_run_never_calls_external_services(tmp_path):
    result = asyncio.run(run_session(count=100, execute=False, output_dir=tmp_path))
    assert result["mode"] == "dry_run"
    assert result["count"] == 100
    assert not list(tmp_path.glob("**/*"))


def test_execute_mode_records_dashboard_with_injected_clients(tmp_path):
    def ask(question):
        return {"executive_summary": f"Evidence-led answer for {question['ticker']}", "sources": [{"source": "NSE"}]}

    def evaluate(question, answer):
        return ({
            "dimensions": {
                "entity_correctness": 100, "numerical_accuracy": 90,
                "evidence_support": 90, "financial_reasoning": 80,
                "freshness": 90, "completeness": 80, "communication": 90,
            },
            "root_causes": [], "critical_failures": [], "notes": "grounded",
        }, {"input_tokens": 20, "output_tokens": 10, "model_calls": 1})

    result = asyncio.run(run_session(
        count=3, execute=True, concurrency=2, output_dir=tmp_path,
        ask_fn=ask, evaluate_fn=evaluate,
    ))
    assert result["completed"] == 3
    assert result["passed"] == 3
    assert result["model_calls"] == 3
    assert result["total_tokens"] == 90
    assert len((tmp_path / "evaluations.jsonl").read_text().splitlines()) == 3


def test_store_redacts_secret_fields(tmp_path):
    path = tmp_path / "events.jsonl"
    append_jsonl(path, {"OPENAI_API_KEY": "secret-value", "nested": {"authorization": "Bearer x"}, "safe": "ok"})
    saved = json.loads(path.read_text())
    assert saved["OPENAI_API_KEY"] == "[REDACTED]"
    assert saved["nested"]["authorization"] == "[REDACTED]"
    assert saved["safe"] == "ok"


def test_unvalidated_large_count_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        asyncio.run(run_session(count=101, execute=False, output_dir=tmp_path))


def test_evaluator_citation_boundary_drops_raw_and_secret_fields():
    rows = _public_citations({"sources": [{
        "title": "NSE filing", "source": "NSE", "date": "2026-08-11",
        "url": "https://nse.example/filing", "raw": {"token": "secret"},
        "headers": {"Authorization": "Bearer secret"},
    }]})
    assert rows == [{
        "title": "NSE filing", "source": "NSE", "date": "2026-08-11",
        "url": "https://nse.example/filing",
    }]
    assert "secret" not in json.dumps(rows)
