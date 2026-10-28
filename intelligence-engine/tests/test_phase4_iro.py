"""Phase 4 acceptance — Institutional Research Orchestration."""

from __future__ import annotations

from institutional_reasoning.iro.adaptive import routes_for
from institutional_reasoning.iro.dag import build_dag, execution_plan
from institutional_reasoning.iro.memory import recall, reset_memory, snapshot
from institutional_reasoning.iro.orchestrator import plan_research, run_assignment
from institutional_reasoning.iro.planning_suite import run_planning_suite
from institutional_reasoning.iro.policies import classify_goal, tasks_for
from institutional_reasoning.iro.schema import PHASE4_TARGETS, ResearchTask
from institutional_reasoning.iro.telemetry import orchestration_summary, task_rows


def setup_function() -> None:
    reset_memory()


# ------------------------------------------------------------------ planner
def test_objective_becomes_structured_plan():
    plan = plan_research("Should I invest £1,000,000 in Infosys?")
    goal = plan["goal"]
    assert goal["goal_type"] == "investment"
    assert goal["entity_id"] == "INFY"
    assert goal["amount"] == "£1,000,000"
    task_ids = {t["task_id"] for t in plan["tasks"]}
    assert {"business_quality", "accounting", "valuation", "risk", "portfolio"} <= task_ids
    assert plan["plan_resolved"] is True
    assert plan["deliverables"]


def test_planner_policy_selection_per_goal_type():
    assert classify_goal("Acquire Wipro")["goal_type"] == "ma"
    assert classify_goal("Evaluate the IPO of Zomato")["goal_type"] == "ipo"
    assert classify_goal("Assess credit exposure for HDFC Bank")["goal_type"] == "credit"
    assert classify_goal("Monitor Infosys")["goal_type"] == "monitoring"
    assert {t.task_id for t in tasks_for("ma")} >= {"synergies", "competition", "valuation"}
    assert {t.task_id for t in tasks_for("credit")} >= {"liquidity", "leverage", "cash_flow"}


# ---------------------------------------------------------------------- DAG
def test_dag_levels_respect_dependencies_and_enable_parallelism():
    plan = plan_research("Should I invest in Infosys?")
    dag, schedule = plan["dag"], plan["execution_plan"]
    assert dag["acyclic"] is True
    assert not dag["dangling"]
    level_of = {tid: i for i, lvl in enumerate(schedule["levels"]) for tid in lvl}
    for node in dag["nodes"]:
        for dep in node["depends_on"]:
            assert level_of[dep] < level_of[node["task_id"]]
    # Independent workstreams share a level
    assert schedule["max_parallelism"] >= 3
    assert schedule["parallel_groups"]


def test_dag_detects_cycles():
    tasks = [
        ResearchTask("a", "A", "q", depends_on=("b",)),
        ResearchTask("b", "B", "q", depends_on=("a",)),
    ]
    dag = build_dag(tasks)
    assert dag["acyclic"] is False
    assert set(dag["cycle"]) == {"a", "b"}
    assert execution_plan(dag)["acyclic"] is False


def test_dag_reports_dangling_dependency():
    dag = build_dag([ResearchTask("a", "A", "q", depends_on=("ghost",))])
    assert dag["dangling"] == ["ghost"]


# ----------------------------------------------------------------- adaptive
def test_alternative_routes_for_missing_history():
    routes = [r["route"] for r in routes_for(["historical_pe"], {})]
    assert routes[:2] == ["sector_valuation", "peer_valuation"]


def test_negative_earnings_switches_multiple_family():
    routes = routes_for([], {"current_pe": "impossible_negative_multiple"})
    assert routes
    assert routes[0]["route"] == "ev_sales"
    assert "EV" in routes[0]["question"] or "EV" in routes[0]["rationale"]


def test_missing_history_triggers_adaptation_not_stop():
    package = run_assignment("Should I invest in Nifty Bank?", ticker_hint="NIFTYBANK")
    valuation = next(t for t in package["tasks"] if t["task_id"] == "valuation")
    assert valuation["adaptations"], "planner must attempt alternative routes"
    assert valuation["status"] in {"adapted", "insufficient"}
    # Never a fabricated recommendation
    assert package["investment_committee"]["can_recommend"] is False


# ---------------------------------------------------------------- workspace
def test_research_package_is_complete_with_per_task_djg():
    package = run_assignment("Should I invest £1,000,000 in Infosys?", ticker_hint="INFY")
    completeness = package["completeness"]
    assert completeness["complete"] is True
    assert completeness["djg_coverage_pct"] == PHASE4_TARGETS["djg_coverage"]
    # Every task carries its own valid justification graph
    for task in package["tasks"]:
        graph = task["justification_graph"]
        assert graph["nodes"]
        assert graph["integrity"]["valid"] is True, graph["integrity"]["problems"]
    assert package["recommendation"]
    assert package["stance"]


def test_specialised_committees_then_investment_committee():
    package = run_assignment("Should I invest in Infosys?", ticker_hint="INFY")
    committees = package["committees"]
    assert {"valuation", "business", "accounting"} <= set(committees)
    for name, committee in committees.items():
        assert committee["stance"]
        assert committee["n_tasks"] >= 1
    ic = package["investment_committee"]
    # Investment committee only merges member stances
    assert set(ic["member_stances"]) == set(committees)
    assert ic["stance"] in {"Evidence-supported", "Partial evidence", "Insufficient evidence"}


def test_optional_gaps_do_not_fabricate_recommendation():
    package = run_assignment("Should I invest in Infosys?", ticker_hint="INFY")
    ic = package["investment_committee"]
    if ic["optional_gap_tasks"]:
        assert ic["can_recommend"] is False
        assert "withheld" in ic["recommendation"].lower()


# ------------------------------------------------------------------- memory
def test_research_memory_enables_plan_reuse():
    assert snapshot()["n_plans"] == 0
    run_assignment("Should I invest in Infosys?", ticker_hint="INFY")
    assert snapshot()["n_plans"] >= 1
    reused = recall("investment", "INFY")
    assert reused is not None
    assert reused["task_ids"]
    assert reused["reuse_count"] >= 1
    # Second assignment on the same goal finds the stored plan
    again = plan_research("Should I invest in Infosys?")
    assert again["reused_plan"] is not None


# ---------------------------------------------------------------- telemetry
def test_orchestration_telemetry_is_measurable():
    package = run_assignment("Should I invest in Infosys?", ticker_hint="INFY")
    rows = task_rows(package)
    assert rows
    for row in rows:
        assert row["task_id"]
        assert row["duration_ms"] >= 0
        assert row["djg_valid"] is True
        assert isinstance(row["depends_on"], list)
    summary = orchestration_summary(package)
    assert summary["tasks"] == len(package["tasks"])
    assert summary["djg_coverage_pct"] == 100.0
    assert summary["max_parallelism"] >= 2
    # Parallel execution must not exceed summed task time
    assert summary["wall_clock_ms"] <= summary["total_duration_ms"] + 500


# ------------------------------------------------------------- phase 4 gate
def test_institutional_planning_suite_gate():
    ips = run_planning_suite()
    assert ips["score"] >= PHASE4_TARGETS["planning_suite"], ips["results"]
    assert ips["avg_djg_coverage_pct"] >= PHASE4_TARGETS["djg_coverage"]
    assert ips["phase4_gate"]["passed"] is True
