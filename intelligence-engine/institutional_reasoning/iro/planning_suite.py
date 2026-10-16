"""Module 10 — Institutional Planning Suite (IPS).

Evaluates planning quality, dependency resolution and orchestration —
not only answer correctness.
"""

from __future__ import annotations

from typing import Any

from institutional_reasoning.iro.orchestrator import plan_research, run_assignment
from institutional_reasoning.iro.schema import IRO_VERSION, PHASE4_TARGETS

IPS_VERSION = "institutional-planning-suite-v1.0.0"


def _assignments() -> list[dict[str, Any]]:
    return [
        {
            "case_id": "ips_001",
            "objective": "Should I invest £1,000,000 in Infosys?",
            "goal_type": "investment",
            "entity_id": "INFY",
            "expect_tasks": ("business_quality", "accounting", "valuation", "risk", "portfolio"),
            "expect_committees": ("valuation", "business", "accounting", "risk", "portfolio"),
            "expect_amount": True,
        },
        {
            "case_id": "ips_002",
            "objective": "Should the portfolio office buy TCS?",
            "goal_type": "investment",
            "entity_id": "TCS",
            "expect_tasks": ("business_quality", "valuation", "portfolio"),
            "expect_committees": ("valuation", "business"),
        },
        {
            "case_id": "ips_003",
            "objective": "Acquire Wipro — evaluate the acquisition.",
            "goal_type": "ma",
            "entity_id": "WIPRO",
            "expect_tasks": ("target_quality", "competition", "synergies", "valuation"),
            "expect_committees": ("business", "valuation"),
        },
        {
            "case_id": "ips_004",
            "objective": "Assess credit exposure and leverage for HDFC Bank.",
            "goal_type": "credit",
            "entity_id": "HDFCBANK",
            "expect_tasks": ("liquidity", "leverage", "cash_flow"),
            "expect_committees": ("accounting",),
        },
        {
            "case_id": "ips_005",
            "objective": "Evaluate the IPO of Zomato.",
            "goal_type": "ipo",
            "entity_id": "ZOMATO",
            "expect_tasks": ("growth", "governance", "market", "valuation"),
            "expect_committees": ("business", "valuation"),
            "expect_adaptation": True,
        },
        {
            "case_id": "ips_006",
            "objective": "Should I invest in Nifty Bank versus history?",
            "goal_type": "investment",
            "entity_id": "NIFTYBANK",
            "expect_tasks": ("valuation",),
            "expect_adaptation": True,
            "expect_withhold": True,
        },
        {
            "case_id": "ips_007",
            "objective": "Monitor Infosys for valuation and accounting changes.",
            "goal_type": "monitoring",
            "entity_id": "INFY",
            "expect_tasks": ("valuation", "accounting"),
            "expect_committees": ("valuation", "accounting"),
        },
        {
            "case_id": "ips_008",
            "objective": "Should I invest in Infosys?",
            "goal_type": "investment",
            "entity_id": "INFY",
            "expect_tasks": ("valuation",),
            "expect_reuse": True,
        },
    ]


def _grade(case: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    package = run_assignment(case["objective"], ticker_hint=case.get("entity_id"))
    goal = package.get("goal") or {}
    dag = package.get("dag") or {}
    schedule = package.get("execution_plan") or {}
    tasks = {t["task_id"]: t for t in package.get("tasks") or []}
    committees = package.get("committees") or {}
    ic = package.get("investment_committee") or {}
    completeness = package.get("completeness") or {}

    # Goal classification
    if goal.get("goal_type") != case["goal_type"]:
        failures.append(f"goal_type={goal.get('goal_type')} expected {case['goal_type']}")
    if case.get("entity_id") and goal.get("entity_id") != case["entity_id"]:
        failures.append(f"entity={goal.get('entity_id')}")
    if case.get("expect_amount") and not goal.get("amount"):
        failures.append("amount not captured")

    # Plan / DAG integrity
    if not dag.get("acyclic"):
        failures.append("dag not acyclic")
    if dag.get("dangling"):
        failures.append(f"dangling dependencies {dag['dangling']}")
    if not (package.get("plan") or {}).get("plan_resolved"):
        failures.append("plan not resolved")

    # Dependency ordering: every dependency must appear in an earlier level
    level_of = {tid: i for i, lvl in enumerate(schedule.get("levels") or []) for tid in lvl}
    for node in dag.get("nodes") or []:
        for dep in node.get("depends_on") or []:
            if level_of.get(dep, -1) >= level_of.get(node["task_id"], 0):
                failures.append(f"dependency order violated: {dep} -> {node['task_id']}")

    # Expected tasks planned and executed
    for tid in case.get("expect_tasks") or ():
        if tid not in tasks:
            failures.append(f"missing task {tid}")

    # Committees present
    for c in case.get("expect_committees") or ():
        if c not in committees:
            failures.append(f"missing committee {c}")
    if not ic.get("stance"):
        failures.append("no investment committee stance")

    # Adaptive replanning
    if case.get("expect_adaptation"):
        adapted = any(
            t.get("adaptations") for t in package.get("tasks") or []
        )
        if not adapted:
            failures.append("expected adaptive replanning attempt")

    # Transparent withholding
    if case.get("expect_withhold"):
        if ic.get("can_recommend") is True:
            failures.append("expected withheld recommendation")

    # Research package completeness + DJG coverage
    if not completeness.get("complete"):
        failures.append(f"package incomplete: {completeness}")
    if float(completeness.get("djg_coverage_pct") or 0) < PHASE4_TARGETS["djg_coverage"]:
        failures.append(f"djg coverage {completeness.get('djg_coverage_pct')}")

    # Plan reuse
    if case.get("expect_reuse") and not (package.get("plan") or {}).get("reused_plan"):
        failures.append("expected plan reuse from research memory")

    orchestration = package.get("orchestration") or {}
    return {
        "case_id": case["case_id"],
        "objective": case["objective"],
        "goal_type": goal.get("goal_type"),
        "passed": not failures,
        "failures": failures,
        "tasks": len(package.get("tasks") or []),
        "levels": schedule.get("sequential_depth"),
        "max_parallelism": schedule.get("max_parallelism"),
        "stance": ic.get("stance"),
        "djg_coverage_pct": completeness.get("djg_coverage_pct"),
        "success_rate_pct": orchestration.get("success_rate_pct"),
        "duration_ms": package.get("duration_ms"),
    }


def run_planning_suite() -> dict[str, Any]:
    results = [_grade(c) for c in _assignments()]
    passed = sum(1 for r in results if r["passed"])
    score = round(100.0 * passed / max(1, len(results)), 2)
    djg = [float(r.get("djg_coverage_pct") or 0) for r in results]
    gate = {
        "planning_suite": score >= PHASE4_TARGETS["planning_suite"],
        "dependency_resolution": all(
            not any("dependency" in f or "dag" in f or "dangling" in f for f in r["failures"])
            for r in results
        ),
        "djg_coverage": (round(sum(djg) / len(djg), 2) if djg else 0.0)
        >= PHASE4_TARGETS["djg_coverage"],
        "package_completeness": all(
            not any("package incomplete" in f for f in r["failures"]) for r in results
        ),
    }
    return {
        "suite": "Institutional Planning Suite",
        "version": IPS_VERSION,
        "iro_version": IRO_VERSION,
        "n": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "score": score,
        "avg_djg_coverage_pct": round(sum(djg) / len(djg), 2) if djg else 0.0,
        "targets": PHASE4_TARGETS,
        "phase4_gate": {"checks": gate, "passed": all(gate.values())},
        "results": results,
    }


def plan_only_inventory() -> dict[str, Any]:
    """Fast planning-quality check without executing frameworks."""
    rows = []
    for case in _assignments():
        plan = plan_research(case["objective"], ticker_hint=case.get("entity_id"))
        rows.append(
            {
                "case_id": case["case_id"],
                "goal_type": (plan.get("goal") or {}).get("goal_type"),
                "tasks": len(plan.get("tasks") or []),
                "levels": (plan.get("execution_plan") or {}).get("sequential_depth"),
                "max_parallelism": (plan.get("execution_plan") or {}).get("max_parallelism"),
                "resolved": plan.get("plan_resolved"),
            }
        )
    return {"version": IPS_VERSION, "n": len(rows), "plans": rows}
