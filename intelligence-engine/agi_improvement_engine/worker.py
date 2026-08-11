"""Reliable evaluation worker for repeated Ask AGI improvement cycles."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from agi_improvement_engine.evaluator import evaluate_answer
from agi_improvement_engine.questions import generate_questions
from agi_improvement_engine.schema import (
    ENGINE_VERSION, RAMP_STAGES, SAFE_DEFAULT_CONCURRENCY, SAFE_DEFAULT_MAX_QUESTIONS,
    SAFE_MAX_CONCURRENCY,
)
from agi_improvement_engine.scoring import score_evaluation
from agi_improvement_engine.store import append_jsonl


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _post_question(endpoint: str, question: dict[str, Any], timeout: float) -> dict[str, Any]:
    query = urllib.parse.urlencode({"question": question["question"], "ticker": question["ticker"]})
    body = json.dumps({"request_id": question["question_id"]}).encode()
    request = urllib.request.Request(f"{endpoint.rstrip('/')}/v1/ui/search?{query}", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


async def run_session(
    *, count: int = SAFE_DEFAULT_MAX_QUESTIONS, endpoint: str = "", execute: bool = False,
    concurrency: int = SAFE_DEFAULT_CONCURRENCY, output_dir: Path | None = None,
    ask_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    evaluate_fn: Callable[[dict[str, Any], dict[str, Any]], tuple[dict[str, Any], dict[str, int]]] = evaluate_answer,
) -> dict[str, Any]:
    if count not in RAMP_STAGES and count > SAFE_DEFAULT_MAX_QUESTIONS:
        raise ValueError(f"count above 100 must use a validated ramp stage: {RAMP_STAGES}")
    concurrency = max(1, min(int(concurrency), SAFE_MAX_CONCURRENCY))
    max_model_calls = max(1, int(os.environ.get("AGI_IMPROVEMENT_MAX_MODEL_CALLS", "100")))
    if execute and count > max_model_calls:
        raise ValueError(f"count exceeds AGI_IMPROVEMENT_MAX_MODEL_CALLS={max_model_calls}")
    questions = generate_questions(count)
    session_id = f"aiei-{uuid4().hex[:12]}"
    out = output_dir or Path(os.environ.get("AGI_IMPROVEMENT_OUTPUT_DIR", "/tmp/agi-improvement"))
    if not execute:
        return {"session_id": session_id, "version": ENGINE_VERSION, "mode": "dry_run", "questions": questions, "count": len(questions)}
    if not ask_fn and not endpoint:
        raise ValueError("endpoint is required in execute mode")
    semaphore = asyncio.Semaphore(concurrency)
    rows: list[dict[str, Any]] = []

    async def one(question: dict[str, Any]) -> None:
        async with semaphore:
            started = time.perf_counter()
            try:
                answer = await asyncio.to_thread(ask_fn or _post_question, question) if ask_fn else await asyncio.to_thread(
                    _post_question, endpoint, question, float(os.environ.get("AGI_ASK_TIMEOUT_SEC", "70"))
                )
                evaluation, usage = await asyncio.to_thread(evaluate_fn, question, answer)
                score = score_evaluation(evaluation)
                status = "passed" if score["passed"] else "failed"
                error = None
            except Exception as exc:
                answer, usage = {}, {"input_tokens": 0, "output_tokens": 0, "model_calls": 0}
                score = score_evaluation({"dimensions": {}, "root_causes": ["SYSTEM_FAILURE"], "notes": str(exc)})
                status, error = "error", f"{type(exc).__name__}: {str(exc)[:300]}"
            row = {
                "session_id": session_id, "timestamp": _utc(), "question": question,
                "status": status, "latency_ms": int((time.perf_counter() - started) * 1000),
                "score": score, "usage": usage, "error": error,
                "answer_trace": {
                    "ask_trace_id": (answer.get("ask_orchestration") or {}).get("ask_trace_id") if isinstance(answer, dict) else None,
                    "sources": answer.get("sources") if isinstance(answer, dict) else None,
                    "as_of": answer.get("as_of") if isinstance(answer, dict) else None,
                },
            }
            rows.append(row)
            append_jsonl(out / "evaluations.jsonl", row)
            if not score["passed"]:
                append_jsonl(out / "learning_events.jsonl", {
                    "event_id": f"learn-{uuid4().hex[:12]}", "session_id": session_id,
                    "timestamp": row["timestamp"], "triggering_question": question,
                    "original_score": score["score"], "root_causes": score["root_causes"],
                    "critical_failures": score["critical_failures"],
                    "affected_subsystem": score["root_causes"][0] if score["root_causes"] else "UNCLASSIFIED",
                    "proposed_change": None, "implementation": None, "regression_tests": [],
                    "new_score": None, "affected_question_classes": [question["kind"], question["difficulty"]],
                    "confidence_in_improvement": None, "status": "DIAGNOSIS_REQUIRED",
                    "answer_is_evidence": False,
                })

    await asyncio.gather(*(one(q) for q in questions))
    causes = Counter(c for row in rows for c in row["score"]["root_causes"])
    passed = sum(1 for row in rows if row["score"]["passed"])
    total_tokens = sum(row["usage"].get("input_tokens", 0) + row["usage"].get("output_tokens", 0) for row in rows)
    input_tokens = sum(row["usage"].get("input_tokens", 0) for row in rows)
    output_tokens = sum(row["usage"].get("output_tokens", 0) for row in rows)
    input_rate = float(os.environ.get("AGI_EVAL_INPUT_USD_PER_MILLION", "0"))
    output_rate = float(os.environ.get("AGI_EVAL_OUTPUT_USD_PER_MILLION", "0"))
    estimated_cost = round((input_tokens * input_rate + output_tokens * output_rate) / 1_000_000, 6)
    dimension_names = tuple(next(iter(rows), {}).get("score", {}).get("weighted_dimensions", {}).keys())
    dimension_averages = {
        name: round(sum(row["score"]["weighted_dimensions"].get(name, 0) for row in rows) / max(1, len(rows)), 2)
        for name in dimension_names
    }
    report = {
        "session_id": session_id, "version": ENGINE_VERSION, "mode": "execute",
        "started_questions": len(questions), "completed": len(rows), "passed": passed,
        "failed": len(rows) - passed, "pass_rate": round(100 * passed / max(1, len(rows)), 2),
        "average_score": round(sum(row["score"]["score"] for row in rows) / max(1, len(rows)), 2),
        "critical_failures": sum(1 for row in rows if row["score"]["critical_failure"]),
        "average_latency_ms": round(sum(row["latency_ms"] for row in rows) / max(1, len(rows))),
        "model_calls": sum(row["usage"].get("model_calls", 0) for row in rows),
        "input_tokens": input_tokens, "output_tokens": output_tokens,
        "total_tokens": total_tokens, "estimated_api_cost_usd": estimated_cost,
        "cost_rate_configured": bool(input_rate or output_rate),
        "dimension_weighted_averages": dimension_averages,
        "top_root_causes": causes.most_common(10),
        "companies_covered": len({q["ticker"] for q in questions}),
        "sectors_covered": len({q["sector"] for q in questions}), "finished_at": _utc(),
        "automatic_code_changes": False, "automatic_merge_or_deploy": False,
    }
    (out / "reports").mkdir(parents=True, exist_ok=True)
    (out / "reports" / f"{session_id}.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Ask AGI controlled investment-intelligence evaluator")
    parser.add_argument("--count", type=int, default=SAFE_DEFAULT_MAX_QUESTIONS)
    parser.add_argument("--endpoint", default=os.environ.get("AGI_ENGINE_URL", ""))
    parser.add_argument("--concurrency", type=int, default=SAFE_DEFAULT_CONCURRENCY)
    parser.add_argument("--execute", action="store_true", help="Spend API credits and call Ask AGI; default is dry-run")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    result = asyncio.run(run_session(count=args.count, endpoint=args.endpoint, execute=args.execute, concurrency=args.concurrency, output_dir=args.output_dir))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
