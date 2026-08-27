# AGI Phase 4 Sprint 4.5 — Institutional Confidence Calibration (ICC)

```text
COMPANY: AGI
MODULE: ICC
VERSION: institutional-confidence-calibration-v1.0.0
PROFILE: icc-confidence-profile-v1.0.0
STATUS: FROZEN v1.0.0 — part of AGI v3.6 Institutional Judgment Release
PHASE: 4 COMPLETE (judgment stack frozen)
```

## Purpose

Compute **institutional confidence** as an emergent property of the full judgment pipeline — not a cosmetic label, not optimism, not an LLM score.

```text
IEW → IHG → IHE → ICR → ICC → Reasoning → ICE
```

Example:

> Confidence: 87/100 because evidence quality is high, committee convergence is strong, historical analogues are consistent, but management guidance is missing.

## Dimensions

Evidence Quality · Evidence Coverage · Hypothesis Strength · Hypothesis Separation ·
Conflict Level (inverted) · Committee Agreement · Historical Analogue Quality ·
Framework Consistency · Missing Evidence (penalty) · Temporal Integrity · Replay Integrity

## InstitutionalConfidenceReport

`overall_confidence` · `confidence_level` · component scores · `missing_evidence_penalty` ·
`temporal_integrity` · `replay_integrity` · `confidence_reason` · `confidence_version`

Always expose **numeric score + reason**. Levels are bands over the number (Very High / High / Moderate / Low / Very Low) — never labels alone.

## Penalties

Confidence decreases when critical evidence is missing, the committee disagrees, analogues are weak, conflict is high, coverage is poor, replay/temporal integrity fails, or fixtures are depended on.

**Fixtures never increase confidence. LLMs never increase confidence.**

## LangSmith

- `confidence_calibration` — component scores, penalties, final confidence, version

## APIs

`/v1/confidence/{health,dashboard,calculate,report,telemetry,history}`

## Measurement

IEL **Confidence Quality Score (CFQS)** — independent of CIO, HQS, and CQS.

## Frozen upstream

IEW / IHG / IHE / ICR remain frozen — ICC consumes them only.

## Phase 4 exit

After certification, freeze the full judgment stack (IEW→ICC) as v1.0.0 and stop adding judgment layers. Phase 5 should shift to investment decision-making over time.
