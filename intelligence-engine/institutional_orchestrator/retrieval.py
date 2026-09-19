"""UAG-01 retrieval — invoke registered providers; never invent domain state."""

from __future__ import annotations

import time
from typing import Any

from institutional_orchestrator.models import ExecutionStep, InstitutionalQuery
from institutional_orchestrator.object_registry import get


def execute_plan(
    query: InstitutionalQuery,
    *,
    portfolio_id: str = "agi-core-equity",
    policy: str = "family_office",
) -> tuple[tuple[ExecutionStep, ...], dict[str, Any]]:
    """
    Run planned retrievals. Returns updated steps + object payloads by type.

    Stateless: does not write into domain engine ownership stores beyond their
    own production façades (which may cache internally).
    """
    ctx = {
        "question": query.question,
        "intent": query.intent,
        "entities": list(query.entities),
        "portfolio_id": portfolio_id,
        "policy": policy,
    }
    payloads: dict[str, Any] = {}
    steps: list[ExecutionStep] = []

    for step in query.execution_plan:
        reg = get(step.object_type)
        t0 = time.perf_counter()
        if reg is None or reg.retrieve is None:
            steps.append(
                ExecutionStep(
                    step_id=step.step_id,
                    object_type=step.object_type,
                    provider=step.provider,
                    purpose=step.purpose,
                    status="missing",
                    latency_ms=0.0,
                    detail="No registered retrieve provider",
                )
            )
            continue
        try:
            result = reg.retrieve(ctx)
            ms = (time.perf_counter() - t0) * 1000.0
            ok = bool(result.get("ok"))
            soft = bool(result.get("soft_missing"))
            status = "ok" if ok and not soft else ("missing" if soft else ("error" if not ok else "ok"))
            if ok:
                payloads[step.object_type] = result
            steps.append(
                ExecutionStep(
                    step_id=step.step_id,
                    object_type=step.object_type,
                    provider=reg.provider,
                    purpose=step.purpose,
                    status=status,
                    latency_ms=round(ms, 2),
                    detail=str(result.get("error") or result.get("note") or ""),
                )
            )
        except Exception as exc:  # noqa: BLE001
            ms = (time.perf_counter() - t0) * 1000.0
            steps.append(
                ExecutionStep(
                    step_id=step.step_id,
                    object_type=step.object_type,
                    provider=reg.provider,
                    purpose=step.purpose,
                    status="error",
                    latency_ms=round(ms, 2),
                    detail=str(exc),
                )
            )

    return tuple(steps), payloads
