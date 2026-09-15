# AGI Phase 4 Sprint 4.4 — Institutional Committee Reasoning (ICR)

```text
COMPANY: AGI
MODULE: ICR
VERSION: institutional-committee-reasoning-v1.0.0
PROFILE: icr-committee-profile-v1.0.0
STATUS: FROZEN v1.0.0 — part of AGI v3.6 Institutional Judgment Release
```

## Purpose

Model structured **investment-committee deliberation** before reasoning concludes.

```text
IEW → IHG → IHE → ICR → Reasoning → ICE
```

Not a voting engine. Not an LLM debate. Not a multi-agent system.

Committees construct competing institutional cases, test assumptions, then converge.

## Roles (not fixed templates)

| Role | Meaning |
|------|---------|
| **Bull** | Strongest evidence-supported **upside** interpretation |
| **Base** | Interpretation best supported by the **current balance** of evidence |
| **Bear** | Strongest evidence-supported **downside** interpretation |

Do **not** force all three. If evidence supports two, emit two. If insufficient, say so explicitly — never fabricate consensus.

## Each case contains

Case Name · Supporting Evidence · Contradictory Evidence · Underlying Assumptions ·
Required Conditions · Key Catalysts · Key Risks · Invalidation Conditions ·
Confidence · Probability · Evidence Coverage · Historical Analogues ·
Framework Alignment · Missing Evidence

## InstitutionalCommitteeReport

`bull_case` · `base_case` · `bear_case` · `committee_summary` · `preferred_case` ·
`alternative_cases` · `probability_distribution` · `confidence` · `major_uncertainties` ·
`key_disagreements` · `missing_evidence` · `committee_version` · `citations`

Probabilities are **relative support** (not forecasts) and always sum to **100%**.

## LangSmith

- `committee_deliberation`
- `committee_deliberation.case` (per role: probability, confidence, support, conflict, assumptions, risks, catalysts, missing_evidence)

## APIs

`/v1/committee/{health,dashboard,deliberate,report,cases,telemetry,history}`

## Measurement

IEL **Committee Quality Score (CQS)** — independent of CIO and HQS.

## Frozen upstream

IEW / IHG / IHE remain frozen — ICR consumes them only. Reasoning, Framework Selection, ICE, Replay unchanged.

## Next

Sprint **4.5 Confidence Calibration** — confidence as an emergent property of committee deliberation.
