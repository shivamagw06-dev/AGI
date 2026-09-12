"""Run the full E2E-01 product experience validation."""

from __future__ import annotations

import time
from typing import Any, Optional

from product_experience_validation.schema import (
    E2E_NOT_A_BENCHMARK,
    E2E_NOT_AN_ENGINE,
    E2E_NOT_AN_OFFICE,
    E2E_PRODUCT,
    E2E_SPEC,
    E2E_VERSION,
    E2E_WORKSTREAM_ID,
    FREEZE_LOCKS,
    PASS_SCORE,
    PRIMARY_COMPANY,
    PRIMARY_TICKER,
    PRODUCT_ENTRY,
    RUBRIC_WEIGHTS,
)
from product_experience_validation.scoring import score_run
from product_experience_validation import store as e2e_store
from product_experience_validation.workflows import WORKFLOW_RUNNERS

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def run_validation(*, persist: bool = True) -> dict[str, Any]:
    t0 = time.perf_counter()
    workflows: list[dict[str, Any]] = []
    for runner in WORKFLOW_RUNNERS:
        try:
            workflows.append(runner())
        except Exception as exc:  # noqa: BLE001
            workflows.append(
                {
                    "workflow": getattr(runner, "__name__", "unknown"),
                    "name": getattr(runner, "__name__", "unknown"),
                    "checks": [
                        {
                            "ok": False,
                            "code": "CONSISTENCY_FAILURE",
                            "detail": f"workflow crashed: {exc}",
                        }
                    ],
                    "error": str(exc),
                }
            )

    scored = score_run(workflows)
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)

    final_question = (
        "Can an experienced institutional investor perform an entire research workflow—"
        "from discovering an opportunity to reviewing evidence, understanding portfolio "
        "implications, and defining a monitoring plan—using only AGI?"
    )
    answer = "YES" if scored["passed"] else "NOT YET"

    result = {
        "ok": True,
        "workstream_id": E2E_WORKSTREAM_ID,
        "product": E2E_PRODUCT,
        "version": E2E_VERSION,
        "role": "end_to_end_product_experience_validation",
        "not_an_engine": E2E_NOT_AN_ENGINE,
        "not_a_benchmark": E2E_NOT_A_BENCHMARK,
        "not_an_office": E2E_NOT_AN_OFFICE,
        "product_entry": PRODUCT_ENTRY,
        "primary_ticker": PRIMARY_TICKER,
        "primary_company": PRIMARY_COMPANY,
        "pass_score": PASS_SCORE,
        "rubric_weights": dict(RUBRIC_WEIGHTS),
        "freeze_locks": dict(FREEZE_LOCKS),
        "workflows": workflows,
        "score": scored["score"],
        "passed": scored["passed"],
        "dimensions": scored["dimensions"],
        "failure_codes": scored["failure_codes"],
        "summary": scored["summary"],
        "final_question": final_question,
        "final_answer": answer,
        "institutionally_ready": bool(scored["passed"]),
        "elapsed_ms": elapsed_ms,
        "spec": E2E_SPEC,
        "brand": "AGI",
        "buy_sell": None,
        "as_of": now_iso(),
    }
    if persist:
        e2e_store.put_run(result)
    return result


_WF_BY_ID = {
    "WF1": "wf1_morning_brief",
    "WF2": "wf2_company_research",
    "WF3": "wf3_evidence_drilldown",
    "WF4": "wf4_ask_agi",
    "WF5": "wf5_research",
    "WF6": "wf6_portfolio",
    "WF7": "wf7_markets",
    "WF8": "wf8_watchlists",
    "WF9": "wf9_context_awareness",
    "WF10": "wf10_navigation",
    "WF11": "wf11_performance",
    "WF12": "wf12_failure_handling",
    "WF13": "wf13_consistency",
    "WF14": "wf14_historical_blind",
    "WF15": "wf15_benchmark",
}


def run_workflow(workflow_id: str) -> dict[str, Any]:
    from product_experience_validation import workflows as wf_mod

    wid = str(workflow_id or "").strip().upper()
    name = _WF_BY_ID.get(wid) or _WF_BY_ID.get(wid.replace("WORKFLOW", "WF"))
    if not name:
        # allow function-style ids
        candidate = wid.lower()
        fn = getattr(wf_mod, candidate, None)
        if callable(fn):
            return fn()
        return {"ok": False, "error": f"unknown workflow: {workflow_id}"}
    fn = getattr(wf_mod, name)
    return fn()
