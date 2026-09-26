# AGI Phase 4 Sprint 4.2 — Institutional Hypothesis Generation Engine (IHG)

```text
COMPANY: AGI
MODULE: IHG
VERSION: institutional-hypothesis-generation-v1.0.0
CATALOG: ihg-hypothesis-catalog-v1.0.0
STATUS: soft-wired after IEW / before Reasoning
```

## Purpose

Force every analytical question through a **Hypothesis Space** before reasoning:

```text
Evidence → Weighted Evidence → Hypotheses → Reasoning → Communication
```

No LLM. No fabrication. No forced single winner.

## Plural outcomes

When evidence is ambiguous, IHG may return:

* Hypothesis A — 46%
* Hypothesis B — 42%
* Hypothesis C — 12%

Status labels: `Preferred` (clear lead), `Contested` (close leaders), `Rejected`
(weak but retained with explanation), `InsufficientEvidence`.

## Pipeline position

```text
… → IEW → IHG → Reasoning → ICE
```

## Frozen

KF, LIDI, IDI, IERE, IEG, IMAI, IEW, Frameworks, Reasoning, ICE, TIRC, IEL, RCI.

## LangSmith spans

- `hypothesis_generation`
- `hypothesis_generation.score`
- `hypothesis_generation.hypothesis` (per hypothesis)

## APIs

`/v1/hypothesis/{health,dashboard,generate,rank,explain,telemetry,history,configuration}`

## Freeze

**IHG v1.0.0 is FROZEN.** Do not optimise the catalog for benchmark chasing.
See `docs/PHASE4_IEW_IHG_FREEZE.md`.

Next: Sprint **4.3 — Institutional Hypothesis Evaluation Engine (IHE)**.
IEL metric for this layer: **HQS** (`docs/AGI_HYPOTHESIS_QUALITY_SCORE.md`).
