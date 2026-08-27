# AGI v4.0 Phase 5 Sprint 5.1 — Institutional Investment Thesis Engine (ITE)

```text
COMPANY: AGI
RELEASE: AGI v4.0 Institutional Investment Office
MODULE: ITE
VERSION: institutional-investment-thesis-v1.0.0
SCHEMA: ite-thesis-schema-v1.0.0
FOUNDATION: AGI v3.6 judgment stack (FROZEN — consume only)
```

## Philosophy

Phase 1–4 asked: *Can AGI understand markets?*  
Phase 5 asks: *Can AGI manage investment ideas like a CIO?*

A thesis is a **database object**, not a chat answer.

## Consumes (frozen)

```text
Evidence Graph → Memory → IEW → IHG → IHE → ICR → ICC → Investment Thesis
```

## Does not

* Modify judgment stack  
* Emit BUY / SELL (Sprint 5.2 Decision Engine)  
* Auto-size positions  

Default `decision_status = Watch`.

## Lifecycle

`Draft → Under Review → Active → Monitoring → Needs Review → Updated → Closed → Archived`

## Versioning

`v1.0 → v1.1 → v1.2…` on material updates; prior versions retained.

## Ten questions

1. Investment view  
2. Why now?  
3. What is the market missing?  
4–6. Bull / Base / Bear  
7. Catalysts  
8. Risks  
9. Invalidation  
10. Monitoring checklist  

## APIs

`/v1/thesis/{health,dashboard,telemetry,history,create,list,:id,:id/versions}`

Portfolio-style queries via `POST /v1/thesis/list`:

* `confidence_drop_gt: 10`  
* `waiting_for: earnings`  

## Measurement

**ITQS** — Investment Thesis Quality Score (independent of CIO / HQS / CQS / CFQS).

## LangSmith

`investment_thesis` span after `confidence_calibration`.
