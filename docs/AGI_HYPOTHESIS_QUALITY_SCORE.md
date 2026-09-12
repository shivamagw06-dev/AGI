# Hypothesis Quality Score (HQS) — IEL Independent Metric

```text
COMPANY: AGI
METRIC: hypothesis_quality / HQS
VERSION: hqs-v1.1.0
INDEPENDENT_OF_CIO: YES
```

## Why

IEW + IHG are infrastructure. **IHE** evaluates competing explanations.
HQS measures the hypothesis **generation + evaluation** layer independently of CIO.

## Components (v1.1)

| Component | Weight | Measures |
|-----------|-------:|----------|
| Plausibility | 0.10 | 2–5 hypotheses or correct Insufficient Evidence gate |
| Coverage Quality | 0.12 | IHE coverage / family explanation coverage |
| Support Quality | 0.12 | Weighted support completeness |
| Conflict Handling | 0.12 | Conflicts retained and scored (never deleted) |
| Ranking Quality | 0.12 | Preferred / indeterminate / plausible consistency |
| Rejection Quality | 0.10 | Rejected kept with explanations |
| Evaluation Quality | 0.16 | Full IHE dimension reports present |
| Confidence Quality | 0.16 | Missing evidence caps confidence; plural calibrated |

## Suite fields

```text
aggregate.hypothesis_quality.mean_hqs
aggregate.hypothesis_quality.pass_pct
summary.hypothesis_quality_score
row.hqs
row.dimensions.hypothesis_quality
```

## Critical rule

HQS is **not** in `DIMENSION_WEIGHTS`. It must not change IEL overall pass % or CIO scoring.
