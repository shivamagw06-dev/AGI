# AGIB Sprint 3.3 — Framework Optimisation Report

## Measured improvement (IEL institutional_1000 soft)

| Metric | Pre (RCI) | Post (FO) | Δ |
|--------|----------:|----------:|--:|
| Pass % | 88.2 | 92.6 | +4.4 |
| Framework accuracy | 75.3 | 96.3 | +21.0 |
| Intent accuracy | 84.7 | 84.7 | +0.0 |
| Mean score | 83.23 | 87.23 | +4.0 |

CIO-25 soft: **100.0%** pass / mean 89.22 (must not regress).

## What changed

- Question-cue overlays (risk / documents / IT ops / airlines)
- Sector enrichment for banks, NBFC, IT services, airlines
- IFSE → `framework-selection-v1.1.0`
- **Patch Intelligence** briefs (never auto-codes)

## Top remaining clusters

1. [14] 14 questions ↓ intent_mismatch ↓ generic ↓ PORTFOLIO ↓ one patch
2. [7] 7 questions ↓ intent_mismatch ↓ banks ↓ PORTFOLIO ↓ one patch
3. [7] 7 questions ↓ intent_mismatch ↓ fmcg ↓ PORTFOLIO ↓ one patch
4. [7] 7 questions ↓ intent_mismatch ↓ industrials ↓ PORTFOLIO ↓ one patch
5. [7] 7 questions ↓ intent_mismatch ↓ it_services ↓ PORTFOLIO ↓ one patch
6. [7] 7 questions ↓ intent_mismatch ↓ metals ↓ PORTFOLIO ↓ one patch
7. [7] 7 questions ↓ intent_mismatch ↓ nbfc ↓ PORTFOLIO ↓ one patch
8. [6] 6 questions ↓ intent_mismatch ↓ banks ↓ ACCOUNTING ↓ one patch

## Highest-ROI next patch (human review)

```yaml
cluster_id: clu-915967a8fe
affected_questions: 14
expected_gain: {'framework_accuracy': '+0.0%', 'intent_accuracy': '+1.4%', 'overall_benchmark': '+0.49%', 'projected_pass_pct': 93.09, 'projected_framework_accuracy': 96.3, 'heuristic': True}
recommended_pr: cursor/fix-intent-mismatch-generic-4cc0
risk: medium
```

Next sprint: **3.4 Intent Optimisation** (portfolio / intent_mismatch clusters).
