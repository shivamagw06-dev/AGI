# AGI V1.1.2 — Knowledge Integration Layer (KIL-01)

## Mission

> AGI operates as a Knowledge Operating System. Continuous Gather → Learn continuously acquires institutional information. The Knowledge Integration Layer transforms that information into canonical institutional knowledge. The Institutional Evidence Platform validates, versions, and preserves that knowledge. All intelligence engines consume canonical knowledge — not raw providers.

**There must never be two knowledge systems.**

## Pipeline

```text
External Providers
        ↓
Continuous Gather → Learn          ← gathering only
        ↓
Knowledge Integration Layer        ← THIS LAYER
        ↓
Canonical Evidence → Registry → Company Memory → KG → FI
        ↓
Decision Eligibility → Research Pack → Writer → Publishing
```

## Package

`intelligence-engine/institutional_evidence/integration/`

| Module | Role |
|--------|------|
| `events/` | Immutable CGL cycle events |
| `transform/` | KF/CGL → canonical domain models |
| `versioning/` | Knowledge Snapshots (`2026.07.30.overnight`) |
| `confidence/` | Knowledge Confidence (≠ Research Confidence) |
| `coverage_states/` | DISCOVERED → … → CONTINUOUS MONITORING |
| `repair/` | Auto acquire/normalize/validate/publish |
| `health/` | Knowledge Health Mission Control board |
| `expansion.py` | Gate: Nifty 500 only after Top-20 complete |
| `layer.py` | Owns integration; soft-wired after every CGL cycle |
| `orchestrate_ask.py` | Ask path: version check → KIL refresh → pack or block |

## Soft-wire

`continuous_gather_learn/orchestrator.py` calls `integrate_cgl_run(run)` after every successful metrics write.

## Phase 1 (do not expand coverage yet)

Demo end-to-end automation for:

`RELIANCE` · `HDFCBANK` · `TCS` · `INFY` · `ICICIBANK`

Then finish remaining Top-20. **Only then** unlock Nifty 500 expansion (`POST /iep/expansion/nifty500`).

## APIs

- `GET /v1/iep/kil/health`
- `POST /v1/iep/kil/integrate` · `POST /iep/kil/integrate/{ticker}`
- `GET /v1/iep/knowledge-health`
- `GET /v1/iep/knowledge-confidence/{ticker}`
- `GET /v1/iep/coverage-state/{ticker}`
- `GET /v1/iep/snapshots` · `/iep/events`
- `POST /v1/iep/ask/{ticker}`
- `GET /v1/iep/expansion` · `POST /iep/expansion/nifty500`

## Principles

Knowledge is gathered once. Normalized once. Validated once. Versioned forever. Everything else consumes canonical knowledge.
