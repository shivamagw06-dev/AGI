# Sprint 5.1 Brief — Institutional Investment Thesis Engine (ITE)

```text
COMPANY: AGI
PHASE: 5 — Institutional Investment Office
SPRINT: 5.1
MODULE: ITE
PRIORITY: Highest
FOUNDATION: AGI v3.6 (frozen) — consume only
STATUS: Implemented v1.0.0 — see PHASE5_INSTITUTIONAL_INVESTMENT_THESIS.md
RELEASE: AGI v4.0
```

## Objective

Convert institutional judgment into a **persistent Investment Thesis** — a living object that can be monitored, decided upon, and learned from — instead of a disposable chat answer.

## Consumes (frozen)

* IEW ordered / weighted evidence
* IHG hypothesis space
* IHE evaluation report
* ICR `InstitutionalCommitteeReport` (Bull / Base / Bear roles)
* ICC `InstitutionalConfidenceReport` (numeric + reason)
* Evidence Graph + Institutional Memory
* Framework / playbook selection (read-only)

## Must not modify

IEW · IHG · IHE · ICR · ICC · Reasoning · ICE · TIRC · IEL CIO weights · RCI core

## Thesis object (minimum fields)

| Field | Source / notes |
|-------|----------------|
| `thesis_id` | Stable identity |
| `company` / ticker | Entity resolution |
| `investment_view` | Short institutional statement |
| `bull_case` / `base_case` / `bear_case` | From ICR roles (not forced if absent) |
| `evidence` | Top weighted + citations |
| `catalysts` / `risks` / `invalidation` | From committee cases |
| `monitoring_checklist` | Derived from missing evidence + catalysts |
| `expected_holding_period` | Deterministic default bands until IDE |
| `decision_status` | Default `Watch` (IDE owns upgrades) |
| `position_size` | Empty until IDE / Portfolio |
| `confidence` + `confidence_reason` | From ICC |
| `committee_version` / `confidence_version` | Provenance |
| `as_of` / `last_updated` | Temporal |
| `citations` | Replay-safe references |

## APIs (proposed)

`/v1/thesis/{health,dashboard,create,get,list,update,history,telemetry}`

## Mission Control

Institutional Thesis Dashboard — active theses, status distribution, confidence, stale monitors, invalidations.

## LangSmith

Trace: Judgment packs → Thesis construction → Persistence (no LLM-inflated thesis fields).

## Exit gate (when built)

* Deterministic thesis from identical judgment packs
* Replay-safe / as-of aware
* ICR / ICC unchanged
* Decision status does not auto-promote to Buy
* Soft IEL / CIO / HQS / CQS / CFQS held
* Living object retrievable after the chat ends

## Explicit non-goals for 5.1

* No portfolio sizing
* No buy/sell automation
* No monitoring loop (5.4)
* No decision learning (5.5)
* Analysis ≠ Decision (leave to 5.2)
