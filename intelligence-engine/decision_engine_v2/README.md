# Institutional Decision Engine V2 (IDE V2)

**Primary question:** What is the highest-quality institutional decision?

**FINAL architectural component.** After IDE V2, AGIB architecture is frozen. Future work improves evidence, coverage, reasoning, analyst depth, calibration and learning — not new top-level intelligence layers.

Soft orchestrator only. Does not replace analysts, Investment Committee, or CIO. Leaves `decision_engine` V1 intact. No redesign of FIL→SSL stack.

## Flag

`DECISION_ENGINE_V2=true` (`decision_engine_v2` in settings)

## API

- `GET /v1/decision-engine-v2/company/{ticker}`
- `POST /v1/decision-engine-v2/analyse`
- `GET /v1/decision-engine-v2/audit/{id}`
- `GET /v1/decision-engine-v2/monitoring/{ticker}`
- `GET /v1/decision-engine-v2/quality-gates`
- `GET /v1/admin/decision-engine-v2`

## Constitution

Evidence → Reasoning → Committee → Portfolio → Policy → Decision

Recommendation statuses are policy-governed readiness states — never forced Buy/Hold/Sell.
