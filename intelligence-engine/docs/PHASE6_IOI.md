# Phase 6 — Institutional Outcome Intelligence (IOI)

> Continuously measure every portfolio decision against reality.

**Not learning.** Prerequisite for Phase 7 Continuous Adaptive Learning.

```text
Research DJG → PDG → Market Outcome → Prediction Evaluation
  → Framework Attribution → Review Committee → Outcome Record
```

Soft-wire under `institutional_reasoning/ioi/`. Architecture v1.0.1 LOCKED.

## Modules

| Module | Path | What |
| --- | --- | --- |
| Decision Lifecycle | `lifecycle.py` | Durable decision objects (DJG/PDG/weights/expectations) |
| Market Outcome Engine | `market.py` | Versioned returns, alpha, drawdown, corporate actions |
| Prediction Evaluator | `evaluator.py` | Expected vs actual errors + score |
| Framework Attribution | `attribution.py` | Which framework/evidence/scenario/policy was wrong |
| Confidence Calibration | `calibration.py` | IES confidence vs live outcome confidence (report only) |
| Review Committee | `review.py` | Decision / research / risk / portfolio / overall quality |
| Framework Scoreboard | `scoreboard.py` | Live accuracy, trends, failure modes |
| Outcome Graph (OG) | `outcome_graph.py` | Full lifecycle graph linked to DJG + PDG |
| Outcome Memory | `memory.py` | Persist chain — no learning |
| Institutional Outcome Suite | `outcome_suite.py` | ≥95%, 0 unattributed failures |

## Attach point

`ipi.decision.decide_portfolio` → `ioi.track_decision`  
`execution_governance.govern_answer` surfaces `record["ioi"]` with `decision_id`.

Evaluation is explicit: `evaluate_decision(decision_id, market_override=...)`.

## Run

```bash
cd intelligence-engine
python3 -c "from institutional_reasoning.ioi.production import quality_gates; print(quality_gates())"
python3 -m pytest tests/test_phase6_ioi.py -q
```

## Exit gate

| Criterion | Status |
| --- | --- |
| Outcome tracking operational | ✅ |
| Prediction evaluator operational | ✅ |
| Framework attribution operational | ✅ |
| Confidence calibration operational | ✅ |
| Review committee operational | ✅ |
| Outcome memory operational | ✅ |
| Outcome graph operational | ✅ |
| Institutional Outcome Suite ≥95% | ✅ |
| Zero unattributed decision failures | ✅ |

## Non-goals

No Phase 1–5 redesign. No DJG/PDG replacement. **No learning** — framework behaviour is not updated from outcomes (that is Phase 7).
