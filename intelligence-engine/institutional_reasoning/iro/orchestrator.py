"""Module 1 + 5 — Research Planner and Research Workspace.

Goal → Plan → DAG → scheduled execution (parallel where safe) →
per-task DJG → committees → Research Package.
"""

from __future__ import annotations

import re
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from institutional_reasoning.evidence_contracts import resolve_entities
from institutional_reasoning.iro.adaptive import adapt_task
from institutional_reasoning.iro.committees import investment_committee, run_all_committees
from institutional_reasoning.iro.dag import build_dag, execution_plan
from institutional_reasoning.iro.memory import recall, remember
from institutional_reasoning.iro.policies import classify_goal, tasks_for
from institutional_reasoning.iro.schema import (
    IRO_VERSION,
    PHASE4_TARGETS,
    ResearchGoal,
    TaskResult,
)

PLANNER_VERSION = "research-planner-v1.0.0"
MAX_WORKERS = 4

_AMOUNT = re.compile(r"[£$€₹]\s?[\d,]+(?:\.\d+)?\s*(?:million|mn|m|bn|billion|crore|lakh)?", re.I)


def _amount_of(objective: str) -> str | None:
    m = _AMOUNT.search(str(objective or ""))
    return m.group(0).strip() if m else None


def plan_research(objective: str, *, ticker_hint: str | None = None) -> dict[str, Any]:
    """Convert a research objective into a structured, dependency-ordered plan."""
    goal_cls = classify_goal(objective)
    entities = resolve_entities(objective, ticker_hint=ticker_hint)
    primary = entities.get("primary") or {}
    goal = ResearchGoal(
        goal_id=f"goal_{uuid.uuid4().hex[:12]}",
        goal_type=str(goal_cls["goal_type"]),
        objective=str(objective or "")[:500],
        entity_id=primary.get("entity_id"),
        entity_name=primary.get("entity_name") or primary.get("entity_id"),
        amount=_amount_of(objective),
    )
    tasks = tasks_for(goal.goal_type)
    dag = build_dag(tasks)
    schedule = execution_plan(dag)
    reused = recall(goal.goal_type, goal.entity_id)
    return {
        "planner_version": PLANNER_VERSION,
        "iro_version": IRO_VERSION,
        "goal": goal.to_dict(),
        "goal_classification": goal_cls,
        "entity_resolution": entities,
        "tasks": [t.to_dict() for t in tasks],
        "dag": dag,
        "execution_plan": schedule,
        "deliverables": [t.deliverable for t in tasks if t.deliverable],
        "reused_plan": reused,
        "plan_resolved": bool(dag.get("acyclic")) and not dag.get("dangling"),
    }


def _summarize(record: dict[str, Any]) -> str:
    committee = record.get("committee") or {}
    text = str(committee.get("conclusion") or "")
    return text[:400]


def _run_task(
    task: dict[str, Any],
    *,
    entity_name: str,
    ticker_hint: str | None,
    packs: dict[str, Any] | None,
    build_evidence: bool,
) -> dict[str, Any]:
    """Execute one research task through governance (produces its own DJG)."""
    from institutional_reasoning.execution_governance import govern_answer

    started = time.time()
    question = str(task["question_template"]).format(name=entity_name or "the company")

    def run(q: str) -> dict[str, Any]:
        return govern_answer(
            q,
            ticker_hint=ticker_hint,
            packs=dict(packs or {}),
            build_institutional_evidence=build_evidence,
        )

    record = run(question)
    frameworks = record.get("frameworks") or []
    executed = [f for f in frameworks if f.get("status") == "executed"]
    validation = record.get("validation") or {}
    missing = list(validation.get("missing") or [])
    rejected = dict(validation.get("rejected") or {})
    adaptations: list[dict[str, Any]] = []
    routes_considered: list[dict[str, Any]] = []

    # A task is only satisfied when the evidence its own deliverable needs is present.
    task_required = tuple(task.get("required_evidence") or ())
    task_gaps = [f for f in task_required if f in missing]

    status = "executed" if executed and not task_gaps else "insufficient"
    if not executed and frameworks and all(
        f.get("status") == "not_applicable" for f in frameworks
    ):
        status = "not_applicable"

    # Adaptive replanning — try alternative evidence routes before withholding.
    if status == "insufficient" and (missing or rejected):
        adaptation = adapt_task(
            task_label=task.get("label") or task.get("task_id"),
            entity_name=entity_name or "the company",
            missing=task_gaps or missing,
            rejected=rejected,
            run_question=run,
        )
        adaptations = adaptation.get("attempts") or []
        routes_considered = adaptation.get("routes_considered") or []
        if adaptation.get("adapted"):
            record = adaptation["record"]
            status = "adapted"

    confidences = [
        float(f["confidence"])
        for f in (record.get("frameworks") or [])
        if isinstance(f.get("confidence"), (int, float))
    ]
    result = TaskResult(
        task_id=task["task_id"],
        label=task.get("label") or task["task_id"],
        question=str(record.get("question") or question),
        status=status,
        committee=task.get("committee") or "investment",
        confidence=round(sum(confidences) / len(confidences), 3) if confidences else None,
        summary=_summarize(record),
        evidence_pack=(record.get("institutional_evidence") or {}).get("summary") or {},
        justification_graph=record.get("justification_graph") or {},
        missing_evidence=list((record.get("validation") or {}).get("missing") or []),
        adaptations=adaptations,
        duration_ms=int((time.time() - started) * 1000),
        deliverable=task.get("deliverable") or "",
    ).to_dict()
    result["optional"] = bool(task.get("optional"))
    result["committee_stance"] = (record.get("committee") or {}).get("stance")
    result["narrative_allowed"] = record.get("narrative_allowed")
    result["routes_considered"] = routes_considered
    return result


def run_assignment(
    objective: str,
    *,
    ticker_hint: str | None = None,
    packs: dict[str, Any] | None = None,
    build_institutional_evidence: bool = True,
    parallel: bool = True,
) -> dict[str, Any]:
    """Full orchestration: plan → schedule → execute → committees → package."""
    started = time.time()
    assignment_id = f"iro_{uuid.uuid4().hex[:12]}"
    plan = plan_research(objective, ticker_hint=ticker_hint)
    goal = plan["goal"]
    entity_name = goal.get("entity_name") or goal.get("entity_id") or ""
    task_specs = {t["task_id"]: t for t in plan["tasks"]}
    levels = (plan["execution_plan"] or {}).get("levels") or []

    results: list[dict[str, Any]] = []
    hint = ticker_hint or goal.get("entity_id")

    for level in levels:
        batch = [task_specs[tid] for tid in level if tid in task_specs]
        if parallel and len(batch) > 1:
            with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(batch))) as pool:
                futures = [
                    pool.submit(
                        _run_task,
                        t,
                        entity_name=entity_name,
                        ticker_hint=hint,
                        packs=packs,
                        build_evidence=build_institutional_evidence,
                    )
                    for t in batch
                ]
                level_results = [f.result() for f in futures]
        else:
            level_results = [
                _run_task(
                    t,
                    entity_name=entity_name,
                    ticker_hint=hint,
                    packs=packs,
                    build_evidence=build_institutional_evidence,
                )
                for t in batch
            ]
        # Preserve declared level order for deterministic packages
        order = {tid: i for i, tid in enumerate(level)}
        level_results.sort(key=lambda r: order.get(r["task_id"], 0))
        results.extend(level_results)

    committees = run_all_committees(results)
    ic = investment_committee(committees=committees, task_results=results, goal=goal)

    package = {
        "assignment_id": assignment_id,
        "iro_version": IRO_VERSION,
        "objective": plan["goal"]["objective"],
        "goal": goal,
        "goal_classification": plan["goal_classification"],
        "plan": {
            "planner_version": plan["planner_version"],
            "tasks": plan["tasks"],
            "deliverables": plan["deliverables"],
            "reused_plan": plan["reused_plan"],
            "plan_resolved": plan["plan_resolved"],
        },
        "dag": plan["dag"],
        "execution_plan": plan["execution_plan"],
        "tasks": results,
        "committees": committees,
        "investment_committee": ic,
        "recommendation": ic.get("recommendation"),
        "stance": ic.get("stance"),
        "duration_ms": int((time.time() - started) * 1000),
        "targets": PHASE4_TARGETS,
    }

    package["justification_graphs"] = {
        r["task_id"]: r.get("justification_graph") or {} for r in results
    }
    package["completeness"] = _completeness(package)
    remember(goal=goal, plan=plan, dag=plan["dag"], outcome=ic)

    from institutional_reasoning.iro.telemetry import orchestration_summary

    package["orchestration"] = orchestration_summary(package)
    return package


def _completeness(package: dict[str, Any]) -> dict[str, Any]:
    tasks = package.get("tasks") or []
    with_djg = [
        r
        for r in tasks
        if (r.get("justification_graph") or {}).get("nodes")
        and ((r["justification_graph"].get("integrity") or {}).get("valid") is True)
    ]
    with_summary = [r for r in tasks if r.get("summary")]
    return {
        "tasks": len(tasks),
        "djg_valid": len(with_djg),
        "djg_coverage_pct": round(100.0 * len(with_djg) / len(tasks), 2) if tasks else 0.0,
        "summaries_pct": round(100.0 * len(with_summary) / len(tasks), 2) if tasks else 0.0,
        "has_committees": bool(package.get("committees")),
        "has_investment_committee": bool(package.get("investment_committee")),
        "has_recommendation": bool(package.get("recommendation")),
        "complete": bool(
            tasks
            and len(with_djg) == len(tasks)
            and package.get("committees")
            and package.get("investment_committee")
            and package.get("recommendation")
        ),
    }
