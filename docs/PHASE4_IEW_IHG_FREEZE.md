# Phase 4 Freeze — Judgment Stack (superseded by AGI v3.6 release)

```text
COMPANY: AGI
DATE: 2026-07-28
STATUS: FROZEN — see docs/AGI_V3_6_INSTITUTIONAL_JUDGMENT_RELEASE.md
```

## Frozen modules

| Module | Version | Role |
|--------|---------|------|
| **IEW** | `institutional-evidence-weighting-v1.0.0` | Evidence priority before reasoning |
| **Weight profile** | `iew-weight-profile-v1.0.0` | Deterministic scorecard |
| **IHG** | `institutional-hypothesis-generation-v1.0.0` | Hypothesis Space before reasoning |
| **Hypothesis catalog** | `ihg-hypothesis-catalog-v1.0.0` | Deterministic templates |

## Why freeze

Sprints 4.1 and 4.2 build **machinery**, not accuracy lift.

Observed (soft IEL):

| Sprint | CIO / IEL lift |
|--------|---------------:|
| IEW | ~0 |
| IHG | ~0 |

That is expected: reasoning does not yet **evaluate** competing hypotheses.

## Rule

Do **not** tune IEW caps or IHG catalogs to chase IEL/CIO points.

Evolve judgment in:

1. **HQS / CQS / CFQS** (IEL independent metrics)
2. Frozen stack: **IEW · IHG · IHE · ICR · ICC** (Phase 4 complete after ICC certification)

## Pipeline (frozen segment)

```text
… → IEW → IHG → IHE → ICR → ICC → Reasoning → ICE
     (all Phase 4 modules frozen at v1.0.0 after certification)
```
