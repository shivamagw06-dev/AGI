# Context Assembly Engine (CAE) v1.0

Unified intelligence orchestration layer. Assembles one ranked, token-efficient institutional context package before reasoning.

## Position

```text
Ask AGI → CAE → Unified Context Package → KIP → IRP → RSP → Answer
              ├─ KF / KCV / AOI / EVE / IIE / FLE / MEE
              └─ future: PMO / IME / RME / AMS
```

Architecture **v1.0.1 LOCKED**. Additive only — does not redesign or replace any engine.

## Mission

> What is the minimum complete institutional context required to answer this accurately?

## Behaviour

- Query classification + context planning
- Dynamic multi-engine retrieval (parallel, soft-fail)
- Ranking, dedupe, compression, token budgets
- Explainability metadata on every included item
- Intelligent cache
- Ask AGI single gateway when `CAE_ASK_AGI_GATEWAY=true`
- Full fallback to prior multi-engine soft retrieval when CAE disabled

## APIs

`/v1/cae/health` · `/dashboard` · `/context` · `/query-plan` · `/retrieval` · `/cache` · `/metrics` · `/explain/{id}` · `/search`

## Out of scope (v2/v3)

Adaptive personalised policies, RL retrieval, predictive prefetch — not implemented in v1.
