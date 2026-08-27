"""Ask Pipeline production facade — soft observability + runner."""

from __future__ import annotations

from typing import Any

from ask_pipeline import store
from ask_pipeline.dashboard import ask_pipeline_dashboard
from ask_pipeline.pipeline import run_complete_ask
from ask_pipeline.schema import FREEZE_LOCKS, PIPELINE_VERSION, PROGRAMME


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "version": PIPELINE_VERSION,
        "soft_wire_only": True,
        "freeze_locks": FREEZE_LOCKS,
        "api_prefix": "/v1/ask",
        "not_a_reasoning_engine": True,
        "knowledge_factory_primary_retrieval": True,
    }


def dashboard() -> dict[str, Any]:
    return ask_pipeline_dashboard()


def run(**kwargs: Any) -> dict[str, Any]:
    return run_complete_ask(**kwargs)


def get_context(pipeline_id: str) -> dict[str, Any]:
    row = store.get_context(pipeline_id)
    if not row:
        return {"found": False, "pipeline_id": pipeline_id, "reason": "context_unavailable"}
    return {"found": True, "pipeline_id": pipeline_id, "context": row}


def get_execution(pipeline_id: str) -> dict[str, Any]:
    row = store.get_execution(pipeline_id)
    if not row:
        return {"found": False, "pipeline_id": pipeline_id, "reason": "execution_unavailable"}
    return {"found": True, "pipeline_id": pipeline_id, "execution": row}


def get_telemetry(pipeline_id: str | None = None) -> dict[str, Any]:
    if pipeline_id:
        row = store.get_telemetry(pipeline_id)
        if not row:
            return {"found": False, "pipeline_id": pipeline_id, "reason": "telemetry_unavailable"}
        return {"found": True, "pipeline_id": pipeline_id, "telemetry": row}
    return {"found": True, "items": store.list_telemetry(limit=100), "n": len(store.list_telemetry(limit=1000))}


def get_replay(replay_id: str) -> dict[str, Any]:
    row = store.get_replay(replay_id)
    if not row:
        return {"found": False, "replay_id": replay_id, "reason": "replay_unavailable"}
    return {"found": True, "replay_id": replay_id, "replay": row}


def quality_gates_sample() -> dict[str, Any]:
    """Exit-oriented sample across representative intents (no investment advice)."""
    samples = [
        ("What is PE ratio?", None),
        ("Is Infosys valuation rich versus history?", "INFY"),
        ("How is Infosys accounting quality?", "INFY"),
        ("Explain the IT services industry value chain for Infosys", "INFY"),
        ("How do RBI policy moves affect banks?", None),
        ("Should I invest £1,000,000 in Infosys?", "INFY"),
        ("Show historical PE for Infosys over the last decade", "INFY"),
        ("What alternative data supports Infosys demand?", "INFY"),
        ("What is the expectation gap for Infosys guidance?", "INFY"),
        ("Compare Infosys vs TCS on valuation", "INFY"),
    ]
    results = []
    for q, hint in samples:
        out = run_complete_ask(q, ticker_hint=hint)
        results.append(
            {
                "question": q,
                "intent": (out.get("intent") or {}).get("intent"),
                "institutionally_complete": out.get("institutionally_complete"),
                "failures": (out.get("quality_gates") or {}).get("failures") or [],
                "pipeline_id": out.get("pipeline_id"),
                "modules_skipped": (out.get("telemetry") or {}).get("modules_skipped"),
                "decision_id": (out.get("decision_quality") or {}).get("decision_id"),
                "outcome_decision_id": (out.get("outcome") or {}).get("decision_id"),
            }
        )
    passed = all(r.get("institutionally_complete") for r in results)
    return {
        "gate": "COMPLETE_ASK_PIPELINE",
        "version": PIPELINE_VERSION,
        "passed": passed,
        "results": results,
        "freeze_locks": FREEZE_LOCKS,
    }
