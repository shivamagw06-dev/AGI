"""AGIB v2.1 Track 1 — Complete Ask Pipeline acceptance suite."""

from __future__ import annotations

import ast
from pathlib import Path

from ask_pipeline import store
from ask_pipeline.pipeline import run_complete_ask
from ask_pipeline.production import dashboard, health, quality_gates_sample
from ask_pipeline.schema import FREEZE_LOCKS, PIPELINE_VERSION


def setup_function() -> None:
    store.reset()


def test_health_and_freeze_locks() -> None:
    h = health()
    assert h["status"] == "ok"
    assert h["version"] == PIPELINE_VERSION
    assert h["freeze_locks"]["phases_1_7"] is True
    assert FREEZE_LOCKS["knowledge_factory"] is True


def test_education_skips_portfolio_and_outcome() -> None:
    out = run_complete_ask("What is PE ratio?")
    assert (out.get("intent") or {}).get("intent") == "Education"
    assert out["policy"]["run_planner"] is False
    assert out["policy"]["run_portfolio"] is False
    assert out["policy"]["run_outcome_registration"] is False
    assert out["planner"]["status"] == "skipped_by_policy"
    assert out["outcome"]["status"] == "skipped_by_policy"
    assert out["decision_quality"]["status"] == "executed"
    assert out["telemetry"]["latency_ms"] is not None
    assert out["replay_id"]
    assert out.get("institutionally_complete") is True


def test_valuation_runs_kf_planner_dq_outcome() -> None:
    out = run_complete_ask("Is Infosys valuation justified versus history?", ticker_hint="INFY")
    assert out["knowledge"]["status"] == "executed"
    assert out["knowledge"]["primary_engine"] == "knowledge_factory"
    assert out["evidence"]["status"] == "executed"
    assert out["planner"]["status"] in {"executed", "error", "degraded"}
    assert out["dag"]["status"] in {"executed", "degraded"}
    assert (out.get("governance") or {}).get("run_id")
    assert out["decision_quality"]["status"] == "executed"
    assert out["decision_quality"]["recording_only"] is True
    assert out["telemetry"]["modules_executed"]
    assert out["replay_id"]
    assert store.get_replay(out["replay_id"])


def test_accounting_and_industry_and_government() -> None:
    for q, hint, intent_substr in (
        ("How is Infosys accounting quality?", "INFY", "Accounting"),
        ("Explain the IT services industry value chain for Infosys", "INFY", "Industry"),
        ("How do RBI and SEBI policy moves affect banks?", None, "Government"),
    ):
        store.reset()
        out = run_complete_ask(q, ticker_hint=hint)
        assert intent_substr in ((out.get("intent") or {}).get("intent") or "")
        assert out["knowledge"]["status"] == "executed"
        assert out["evidence"]["status"] == "executed"
        assert out["decision_quality"]["status"] == "executed"


def test_portfolio_invokes_portfolio_policy() -> None:
    out = run_complete_ask("Should I invest £1,000,000 in Infosys?", ticker_hint="INFY")
    assert (out.get("intent") or {}).get("intent") == "Portfolio"
    assert out["policy"]["run_portfolio"] is True
    assert out["policy"]["run_outcome_registration"] is True
    assert out["decision_quality"]["status"] == "executed"
    # outcome may execute or error soft — must not be learning
    assert out["outcome"].get("learning") is False
    assert out["policy"]["run_learning"] is False


def test_historical_alt_expectation_comparison() -> None:
    cases = [
        ("Show historical PE for Infosys over the last decade", "INFY", "Historical"),
        ("What alternative data supports Infosys demand?", "INFY", "AlternativeData"),
        ("What is the expectation gap for Infosys guidance?", "INFY", "Expectation"),
        ("Compare Infosys vs TCS on valuation", "INFY", "Comparison"),
    ]
    for q, hint, intent in cases:
        store.reset()
        out = run_complete_ask(q, ticker_hint=hint)
        assert (out.get("intent") or {}).get("intent") == intent
        assert out["telemetry"]["latency_ms"] is not None
        assert out["decision_quality"]["decision_id"]


def test_telemetry_decision_recording_dashboard() -> None:
    out = run_complete_ask("Is Infosys a quality business?", ticker_hint="INFY")
    assert store.get_telemetry(out["pipeline_id"])
    assert store.get_execution(out["pipeline_id"])
    assert store.get_context(out["pipeline_id"])
    dash = dashboard()
    assert dash["questions_total"] >= 1
    assert dash["decision_records"] >= 1
    assert "average_latency_ms" in dash


def test_quality_gates_sample_suite() -> None:
    report = quality_gates_sample()
    assert report["gate"] == "COMPLETE_ASK_PIPELINE"
    assert len(report["results"]) >= 10
    # All samples should be institutionally complete under policy skips
    assert report["passed"] is True


def test_existing_reasoning_and_kf_untouched() -> None:
    """Track 1 must not rewrite Phase 1–7 or KF package sources."""
    root = Path(__file__).resolve().parents[1]
    frozen = [
        root / "institutional_reasoning" / "execution_governance.py",
        root / "institutional_reasoning" / "evidence_contracts.py",
        root / "institutional_reasoning" / "iki" / "planner.py",
        root / "knowledge_factory" / "schedulers" / "daily.py",
        root / "knowledge_factory" / "validators" / "pipeline.py",
    ]
    for path in frozen:
        assert path.exists()
        # Parseable python — structural sanity
        ast.parse(path.read_text(encoding="utf-8"))

    # ask_pipeline must not import cal propose on Ask runner
    pipeline_src = (root / "ask_pipeline" / "pipeline.py").read_text(encoding="utf-8")
    assert "propose_from_outcome" not in pipeline_src
    assert "evaluate_decision" not in pipeline_src
    assert "run_assignment" not in pipeline_src  # avoid multi govern_answer on Ask


def test_preloaded_institutional_memory_is_reused(monkeypatch) -> None:
    import institutional_knowledge_layer.production as ikl_production

    def duplicate_consult(*args, **kwargs):
        raise AssertionError("institutional memory was consulted twice")

    monkeypatch.setattr(ikl_production, "ask_consult", duplicate_consult)
    preloaded = {
        "enabled": True,
        "layers_hit": ["company_memory"],
        "confidence": 0.8,
        "answer_hints": ["Verified prior company memory."],
    }
    out = run_complete_ask(
        "What is the investment thesis on Infosys?",
        ticker_hint="INFY",
        institutional_knowledge=preloaded,
    )
    assert out["knowledge"]["institutional_knowledge"] == preloaded
