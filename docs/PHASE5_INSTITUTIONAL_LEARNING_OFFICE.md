# AGI v4.0 Phase 5 Sprint 5.5 — Institutional Learning Office (ILO)

```text
COMPANY: AGI
RELEASE: AGI v4.0 Institutional Investment Office
MODULE: ILO
VERSION: institutional-learning-office-v1.0.0
SCHEMA: ilo-learning-schema-v1.0.0
STATUS: FINAL Office module — no Sprint 5.6
```

## Philosophy

Learning is **process memory**, not market facts.

```text
Monitoring Event → Outcome → Learning → Knowledge (process) → Future Thesis
```

ILO does **not** update Knowledge Factory.  
ILO does **not** rewrite thesis / decision / portfolio history.

## InvestmentLearning fields

learning_id · thesis_id · decision_id · portfolio_id · outcome ·
expected · actual · difference · root_cause · lesson · future_guidance ·
confidence_change · linked_monitoring_events · linked_evidence · learning_version

## Questions every closed thesis answers

1. What happened?  
2. Were we correct?  
3. If not — why?  
4. Root-cause bucket (Evidence / Timing / Macro / Management / Valuation / Catalyst / Execution)  
5. What should AGI remember? (investment process)

## Categories

Evidence · Framework · Hypothesis · Committee · Monitoring ·
Decision · Portfolio · Timing · Macro · Risk

## APIs

`/v1/learning/{health,dashboard,telemetry,history,create,list,:learning_id}`

## Measurement

**LQS** — Learning Quality Score (independent of CIO / MQS / prior metrics).

## LangSmith

`learning_office` after `monitoring_office`, before `reasoning.governance`.

## Hard rules

* Final Office module — **no Sprint 5.6**  
* Process memory ≠ Knowledge Factory  
* Soft-wire only  
* No positions / orders / execution  
