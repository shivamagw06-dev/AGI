# AGI IEW Evaluation — Phase 4 Sprint 4.1

```text
COMPANY: AGI
SPRINT: Phase 4 · Sprint 4.1 Institutional Evidence Weighting
IEW: institutional-evidence-weighting-v1.0.0
WEIGHT PROFILE: iew-weight-profile-v1.0.0
DATE: 2026-07-28
```

## Method

- Soft-wire IEW into Ask pipeline + IEL soft probe (after TIRC post-analog).
- Run `institutional_1000` + `cio_frozen_25` in **soft** mode (probe path includes IEW).
- Compare against AGI v3.5 **CERTIFIED** frozen baselines (full-path freeze remains the engineering reference).
- Unit acceptance suite validates deterministic ranking invariants (filings ≫ media, fixture ceiling, replay identity).

## Results vs frozen baseline

| Metric | Frozen (v3.5 full) | IEW soft (this sprint) | Delta |
|--------|-------------------:|-----------------------:|------:|
| IEL institutional_1000 pass % | 99.9 | **99.9** | 0 |
| IEL mean score | 90.24 | 90.05 | −0.19 |
| CIO-25 pass % | 100 | **100** | 0 |
| CIO mean score | 87.58 | 87.58 | 0 |
| Reasoning changed | No | **No** | — |
| LLM used for weighting | N/A | **No** | — |

Regression gate (`institutional_evaluation_lab`): `regression=false`.

## Ranking acceptance (unit)

| Check | Result |
|-------|--------|
| Deterministic identical weights | PASS |
| Replay-identical rankings | PASS |
| Audited filings ≫ commentary | PASS |
| Regulator ≫ media | PASS |
| Company filings ≫ rumours | PASS |
| Fixtures never outrank validated live | PASS |
| Temporal rejected → weight 0 / excluded | PASS |
| Analogues score consistently | PASS |
| Contradictions identified, not resolved | PASS |
| Reasoning / framework / ICE / TIRC untouched | PASS (soft-wire only) |

## RCI note

Soft IEL still surfaces pre-existing framework-mismatch clusters (banks / EXPECTATIONS family). These are **not introduced by IEW** (weighting does not alter framework selection). Evidence-quality clusters were not the dominant open RCI set; IEW adds explainable ranking telemetry for future correlation with IEL misses via LangSmith.

## LangSmith observability

Mandatory spans on every Ask:

1. `evidence_weighting` — stage inputs/outputs (counts, top id, average weight)
2. `evidence_weighting.score` — per evidence: raw component scores, ranking position, exclusion reason

Metadata attached: `question_id`, `intent`, `framework`, `playbook`, `replay_mode`, `weight_version`, `reasoning_version`.

**Feedback loop (recommended):** compare high- vs low-scoring IEL answers in LangSmith; promote durable improvements only via a **new versioned weight profile** (never ad-hoc edits to live caps).

## Exit gate

| Gate | Status |
|------|--------|
| Deterministic evidence ranking | ✓ |
| Replay integrity preserved (soft path; TIRC untouched) | ✓ |
| No reasoning / framework / communication regression | ✓ |
| LangSmith traces for every weighting decision | ✓ (instrumented) |
| Evidence ranking explainable | ✓ |
| IEL improves or remains stable | ✓ (pass held at 99.9%) |
| CIO improves or holds | ✓ (100%) |
| RCI evidence-quality clusters decrease | ◐ deferred — needs full-path + LangSmith cohort analysis after production traffic |

## Next

- Sprint 4.2 Hypothesis Generation consumes ordered weighted evidence.
- Sprint 4.3 Contradiction Resolution (IEW only labels today).
- Optional full-path IEL 1,025 re-cert if Phase 4 release board requires measure-only freeze update.
