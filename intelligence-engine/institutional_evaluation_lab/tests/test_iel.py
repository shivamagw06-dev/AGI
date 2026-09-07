"""AGIB Phase 3 Sprint 3.1 — Institutional Evaluation Lab acceptance tests."""

from __future__ import annotations

import ast
from pathlib import Path

from institutional_evaluation_lab import IEL_VERSION, run, status
from institutional_evaluation_lab.datasets.catalog import catalog_stats, load_suite
from institutional_evaluation_lab.production import board, catalog
from institutional_evaluation_lab.schema import CATEGORIES, QUALITY_TARGETS

ROOT = Path(__file__).resolve().parents[1]


def test_iel_health_and_catalogue() -> None:
    assert IEL_VERSION.startswith("institutional-evaluation-lab")
    st = status()
    assert st["status"] == "ready"
    stats = catalog_stats()
    assert stats["cio_frozen_25"] == 25
    assert stats["institutional_1000"] >= 1000
    assert stats["investor_100"] == 100
    assert stats["meets_1000_plus"] is True
    assert stats["all"] >= 1025
    assert set(CATEGORIES).issubset(set(stats["by_category"].keys()))
    assert board()["catalogue"]["meets_1000_plus"] is True
    assert QUALITY_TARGETS["cio_benchmark"] == 9.0


def test_question_schema_fields() -> None:
    q = load_suite("cio_frozen_25")[0]
    for key in (
        "question_id",
        "question",
        "intent",
        "framework",
        "expected_evidence",
        "expected_playbook",
        "expected_confidence",
        "expected_reasoning",
        "ground_truth",
        "acceptable_alternatives",
        "difficulty",
        "category",
        "version",
    ):
        assert key in q


def test_smoke_benchmark_runs() -> None:
    summary = run(suite="smoke", mode="soft", limit=20, persist_baseline=False)
    assert summary["n_questions"] == 20
    assert summary["aggregate"]["n"] == 20
    assert summary["aggregate"]["mean_score"] > 0
    assert "top_root_causes" in summary["aggregate"]
    assert summary["reasoning_changed"] is False
    assert summary["failure_clusters"]["n_clusters"] >= 0


def test_cio_frozen_suite_soft() -> None:
    summary = run(suite="cio_frozen_25", mode="soft", persist_baseline=False)
    assert summary["n_questions"] == 25
    # Soft probe should clear a meaningful share — measurement system works
    assert summary["aggregate"]["pass_pct"] >= 40.0
    assert summary["aggregate"]["mean_score"] >= 50.0
    # Replay Q24 must not invent future leakage failures incorrectly always
    q24 = next(r for r in summary["rows"] if r["question_id"] == "CIO-Q24")
    assert "future_leakage" not in (q24.get("root_causes") or [])


def test_catalog_api_shape() -> None:
    cat = catalog(suite="institutional_1000", limit=10)
    assert cat["n"] == 10
    assert cat["stats"]["institutional_1000"] >= 1000


def test_investor_100_is_a_complete_routable_coverage_suite() -> None:
    questions = load_suite("investor_100")
    assert len(questions) == 100
    assert len({q["question_id"] for q in questions}) == 100
    assert all(q["answer_format"] for q in questions)
    assert all(q["expected_evidence"] for q in questions)
    assert all(q["expected_playbook"] for q in questions)
    cat = catalog(suite="investor_100", limit=100)
    assert cat["n"] == 100


def test_no_llm_imports() -> None:
    banned = ("openai", "anthropic", "litellm", "langchain")
    for path in ROOT.rglob("*.py"):
        if "tests" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not any(b in alias.name.lower() for b in banned)
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not any(b in node.module.lower() for b in banned)


def test_reasoning_untouched_flag() -> None:
    summary = run(suite="smoke", mode="soft", limit=5)
    assert summary["reasoning_changed"] is False
    assert summary["fabricated"] is False
