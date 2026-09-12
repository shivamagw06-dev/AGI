# Market Event Engine (MEE) v1.0

Canonical event detection, normalisation, severity, impact propagation and market timelines.

## Position

```text
AOI → EVE → KCV → KF → IIE → FLE → MEE → KIP → IRP → RSP → Ask AGI
                                         ├─► PMO (future)
                                         ├─► IME (future)
                                         └─► AMS (future)
```

Architecture **v1.0.1 LOCKED**. Additive only — no redesign of KF1, KCV1, AOI, EVE, IIE, FLE, KIP, IRP, RSP, or Ask AGI.

## Mission

Markets move because **events occur**. Every verified change becomes a permanent institutional event object.

## Invariants

- Events are immutable (never overwrite; version instead)
- Never delete — archive / supersede / mark duplicate
- Consume verified EVE / IIE / FLE only — never raw documents
- Propagation is asynchronous and idempotent

## APIs

`/v1/mee/health` · `/dashboard` · `/events` · `/company/{key}` · `/sector/{id}` · `/theme/{id}` · `/timeline` · `/impact/{id}` · `/relationships` · `/history` · `/similar/{id}` · `/search` · `/consult` · `/cycle`

## Ask AGI

Soft field `market_events` on SearchView via `MeeService.consult` — retrieve **what changed** before reasoning.

## Out of scope (v2/v3)

Event embeddings, streaming ingestion, causal chain learning — not implemented in v1.
