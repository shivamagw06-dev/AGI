# AGI v4.0 Phase 5 Sprint 5.2 — Institutional Decision Office (IDO)

```text
COMPANY: AGI
RELEASE: AGI v4.0 Institutional Investment Office
MODULE: IDO
VERSION: institutional-decision-office-v1.0.0
SCHEMA: ido-decision-schema-v1.0.0
FOUNDATION: AGI v3.6 judgment (frozen) + ITE theses (consume only)
```

## Philosophy

Analysis ≠ Decision.

```text
Investment Thesis  →  Decision Office  →  InvestmentDecision
```

Most institutional decisions are **not** BUY.

## Decision types

Wait · Monitor · Increase Research · Reject · Escalate · Approve ·
Review After Earnings · Review After Budget · Review After Results

**Never:** orders, execution, BUY/SELL as trade instructions.  
`Approve` means process approval for continued governance — not an order.

## InvestmentDecision fields

`decision` · `reason` · `required_conditions` · `dependencies` · `confidence` ·
`owner` · `review_date` · `review_trigger` · `status` · `version`

## Lifecycle

`Watch → Research → Committee Review → Approved → Monitoring → Closed`

## APIs

`/v1/decision/{health,dashboard,telemetry,history,deliberate,list,:id,:id/versions}`

## Measurement

**DQS** — Decision Quality Score (independent of CIO / HQS / CQS / CFQS / ITQS).

## LangSmith

`decision_office` span after `investment_thesis`.
