"""S07 — Research planner soft-wire (existing IRO plan_research only)."""

from __future__ import annotations

import time
from typing import Any

from app.tools.registry import plan_tools


def run_planner(
    question: str,
    *,
    ticker_hint: str | None = None,
    policy: dict[str, Any],
) -> dict[str, Any]:
    started = time.time()
    tool_plan = plan_tools(question, ticker_hint=ticker_hint)
    if not policy.get("run_planner"):
        return {
            "stage": "research_planning",
            "status": "skipped_by_policy",
            "reason": (policy.get("skips") or {}).get("planner") or "skipped_by_policy",
            "plan": None,
            "tool_plan": tool_plan,
            "duration_ms": int((time.time() - started) * 1000),
        }
    try:
        from institutional_reasoning.iro.orchestrator import plan_research

        plan = plan_research(question, ticker_hint=ticker_hint)
        return {
            "stage": "research_planning",
            "status": "executed",
            "plan": plan,
            "tool_plan": tool_plan,
            "planner_version": plan.get("planner_version"),
            "plan_resolved": plan.get("plan_resolved"),
            "task_count": len(plan.get("tasks") or []),
            "duration_ms": int((time.time() - started) * 1000),
            "fabricated": False,
        }
    except Exception as exc:
        return {
            "stage": "research_planning",
            "status": "error",
            "error": str(exc)[:200],
            "plan": None,
            "tool_plan": tool_plan,
            "duration_ms": int((time.time() - started) * 1000),
        }
