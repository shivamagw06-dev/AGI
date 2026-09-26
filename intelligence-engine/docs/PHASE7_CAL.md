# Phase 7 — Continuous Adaptive Learning (CAL)

> Controlled, versioned learning from outcome reviews — never silent self-modification.

```text
Outcome Intelligence → Learning Proposal → Simulation → Benchmark
  → Approval → Production Overlay (versioned)
```

Soft-wire under `institutional_reasoning/cal/`. Architecture v1.0.1 LOCKED.

**Never:** Outcome → Production  
**Never:** Rewrite framework source automatically.

## Modules

| Module | Path | What |
| --- | --- | --- |
| Learning Candidate Generator | `candidates.py` | Increase/decrease confidence, applicability, planner, policy, or no change |
| Framework Calibration | `overlays.py` + versions | Small planner weight / confidence overlays |
| Planner Learning | `iki/planner.py` soft-read | Re-rank via approved weights |
| Policy Learning | `ipi/policy.py` soft-read | Propose tighter limits (human approval) |
| Applicability Learning | versions rules | Regime/ticker scoped reductions |
| Confidence Learning | `iki/confidence.py` soft-read | Dynamic blend IES + live overlay |
| Regime Detection | `regime.py` | Segment learning by bull/bear/crisis/… |
| Learning Sandbox | `sandbox.py` | Replay proxy; reject IES regressions |
| Versioned Learning | `versions.py` | Nothing overwritten; reversible overlays |
| Learning Graph | `learning_graph.py` | OG → Proposal → Simulation → Approval → Version |
| Learning Governance Layer | `governance.py` | Propose → Validate → Simulate → Approve → Deploy |
| Institutional Learning Suite | `learning_suite.py` | Exit gate |

## Attach points

- `ioi.evaluate_decision(..., propose_learning=True)` → generates proposals only
- `cal.govern_learning(outcome_record)` → full governed path
- Soft consumers: IKI confidence/planner, IPI policy

## Run

```bash
cd intelligence-engine
python3 -c "from institutional_reasoning.cal.production import quality_gates; print(quality_gates())"
python3 -m pytest tests/test_phase7_cal.py -q
```

## Exit gate

| Criterion | Status |
| --- | --- |
| Proposals from outcome reviews | ✅ |
| No production change without simulation + approval | ✅ |
| Versioned confidence / applicability / planner / policy | ✅ |
| Regime-segmented candidates | ✅ |
| Traceable Learning Graph | ✅ |
| ILS ≥95%, 0 ungoverned, 0 IES regressions on accept | ✅ |

## Non-goals

No Phase 1–6 redesign. No autonomous framework rewrites. No silent production mutation.
