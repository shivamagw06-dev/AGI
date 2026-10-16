# Phase 4 — Institutional Research Orchestration (IRO)

> Coordinate an entire institutional research workflow from a single investment objective.

Not more reasoning, frameworks, or evidence. AGIB now solves a **research assignment** instead of answering a prompt.

```text
Research Goal → Research Plan → Execution DAG → Multiple Judgement Graphs
  → Specialised Committees → Investment Committee → Research Package
```

Soft-wire under `institutional_reasoning/iro/`. Architecture v1.0.1 LOCKED.

## Modules

| Module | Path | What |
| --- | --- | --- |
| Research Planner | `orchestrator.plan_research` | Goal → tasks, dependencies, deliverables |
| Research DAG | `dag.py` | Task graph, cycle + dangling detection |
| Task Scheduler | `dag.execution_plan` | Kahn layering; same level runs in parallel |
| Adaptive Planning | `adaptive.py` | Alternative evidence routes, else withhold |
| Research Workspace | `orchestrator.run_assignment` | Per-task evidence pack, DJG, confidence, summary |
| Committee Orchestration | `committees.py` | Valuation / Business / Accounting / Risk / Portfolio → Investment |
| Research Memory | `memory.py` | Plan reuse (workflow, not outcome learning) |
| Planner Policies | `policies.py` | investment / credit / M&A / IPO / monitoring |
| Orchestration Telemetry | `telemetry.py` | Task, duration, dependencies, DJG, success/failure |
| Institutional Planning Suite | `planning_suite.py` | Grades planning, not just answers |

## Example plan (investment)

```text
level 0 (parallel)  accounting · business_quality · industry · management
level 1 (parallel)  valuation · risk
level 2              portfolio
```

Every task runs through governance, so every task carries **its own Decision Justification Graph**. The investment committee merges committee verdicts — it cannot invent findings.

## Adaptive replanning

| Blocked | Route order |
| --- | --- |
| `historical_pe` / `historical_percentile` | sector valuation → peer valuation |
| `peer_pe` | sector valuation |
| `current_pe` invalid (negative earnings / placeholder) | switch to EV-based multiple |

If every route fails, the package withholds transparently.

## Run

```bash
cd intelligence-engine
python3 -c "from institutional_reasoning.iro.production import quality_gates; print(quality_gates())"
python3 -m pytest tests/test_phase4_iro.py -q
```

## Phase 4 exit gate

| Criterion | Status |
| --- | --- |
| Research planner operational | ✅ |
| Task DAG generation | ✅ |
| Dependency scheduling (parallel levels) | ✅ |
| Adaptive replanning | ✅ |
| Multi-committee orchestration | ✅ |
| Research package generation | ✅ |
| Research memory (plans, not learning) | ✅ |
| Institutional Planning Suite ≥95% | ✅ 100% |
| Every planning decision linked to a DJG | ✅ 100% coverage |

## Note on withholding

A "Partial evidence" package is the honest outcome when optional workstreams (risk, portfolio) have no evidence producers yet. The orchestrator distinguishes **blocking** gaps from **optional** gaps and never issues a portfolio recommendation on incomplete research.
