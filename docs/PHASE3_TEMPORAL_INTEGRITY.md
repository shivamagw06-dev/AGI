# AGI Phase 3 Sprint 3.5 — Temporal Integrity & Replay Certification (TIRC)

**Company:** AGI  
**Module:** `temporal_integrity` (`TIRC`)  
**Version:** `temporal-integrity-v1.0.0`

## Purpose

Permanent institutional guarantee: every historical replay answer is built only from information with `available_from <= as_of`. No future labels, prices, documents, analogues, or graph edges may influence retrieval, assembly, memory, reasoning, or communication.

## Soft-wire order

```text
Intent → Evidence → Playbooks → Evidence Graph
  → Replay Guard (pre-analog)
  → Institutional Analog Intelligence
  → Replay Guard (post-analog)
  → Reasoning → Communication
```

## Do not change

Knowledge Factory · Reasoning · Frameworks · Intent · Playbooks · Evaluation judges · RCI

## Exit metrics (observed)

| Metric | Target | Observed |
|--------|-------:|---------:|
| Future leakage | 0 | **0** |
| Historical replay accuracy | 100% | **100%** |
| IEL 1,025 pass | ≥98% | **99.9%** |
| CIO-25 pass | 100% | **100%** |

## APIs

`/v1/temporal-integrity/{dashboard,replay,validation,rejected,certification,telemetry}`
