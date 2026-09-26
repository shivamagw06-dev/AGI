# AGI Phase 4 Sprint 4.1 — Institutional Evidence Weighting Engine (IEW)

```text
COMPANY: AGI
MODULE: IEW
VERSION: institutional-evidence-weighting-v1.0.0
WEIGHT PROFILE: iew-weight-profile-v1.0.0
STATUS: soft-wired after Institutional Memory / before Reasoning
```

## Purpose

Deterministic, LLM-free ranking of institutional evidence so reasoning receives
**ordered weighted evidence** instead of an unordered collection.

## Pipeline position

```text
Intent → Evidence → Graph → Memory → Temporal Integrity
  → Institutional Evidence Weighting → Reasoning → Communication
```

## Frozen systems (untouched)

Knowledge Factory, LIDI, IDI, IERE, Evidence Graph, IMAI, Intent, Answer Assembly,
Framework Selection, ICE, TIRC / Replay Guard, IEL judges, RCI, Patch Intelligence,
and reasoning internals.

## Weight dimensions (profile v1)

| Dimension | Cap |
|-----------|----:|
| Credibility | 40 |
| Materiality | 22 |
| Freshness | 10 |
| Quality | 8 |
| Corroboration | 8 |
| Analogue | 6 |
| Specificity | 6 |

Every object exposes `weight_score`, `weight_breakdown`, `weight_version`,
`weight_reason` (as `reason`), and `confidence_modifier`.

## LangSmith

Mandatory spans:

- `evidence_weighting` — pipeline stage
- `evidence_weighting.score` — per-evidence decision (raw + component scores,
  ranking position, exclusion reason)

Metadata: `question_id`, `intent`, `framework`, `playbook`, `replay_mode`,
`weight_version`, `reasoning_version`.

## APIs

Prefix: `/v1/evidence-weighting/`

- `GET health|dashboard|telemetry|configuration`
- `POST ranking|score|explain`

## Configuration

Versioned profiles under
`intelligence-engine/institutional_evidence_weighting/config/profiles/`.
Tune weights by adding a new profile version — do not change reasoning code.

## Freeze

**IEW v1.0.0 is FROZEN.** Do not optimise weight profiles for benchmark chasing.
See `docs/PHASE4_IEW_IHG_FREEZE.md`.

## Contradictions

IEW **identifies** higher / lower / equal weight only.
Hypothesis comparison / evaluation is Sprint **4.3 IHE** (Institutional Hypothesis Evaluation).
