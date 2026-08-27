# AGIB Institutional Evaluation Lab — Run Report

**Run ID:** `iel-run-589d8a6eef`  
**Suite:** `institutional_1000`  
**Mode:** `soft`  
**Commit:** `a8474b03`  
**IEL version:** `institutional-evaluation-lab-v1.0.0`  

## Aggregate

| Metric | Value |
|--------|------:|
| Questions | 1000 |
| Pass % | 88.2 |
| Mean score | 83.23 |
| Passed | 882 |
| Failed | 118 |

## Regression

- Status: **ok**
- Deltas: `{'pass_pct': 38.2, 'mean_score': 6.72}`

## Category means

- **accounting**: 68.2 (n=15)
- **company**: 76.48 (n=100)
- **cross_domain**: 89.27 (n=518)
- **documents**: 76.78 (n=120)
- **government**: 94.08 (n=15)
- **historical_replay**: 79.94 (n=55)
- **industry**: 78.69 (n=45)
- **macro**: 90.36 (n=15)
- **portfolio**: 68.14 (n=56)
- **risk**: 75.81 (n=50)
- **valuation**: 72.05 (n=11)

## Top root causes

- `framework_mismatch` — 247
- `intent_mismatch` — 153
- `future_leakage` — 15
- `memory_miss_on_analog_question` — 11

## Failure clusters (top 10)

- **intent_mismatch** (n=103, severity=medium) cats={'accounting': 15, 'company': 36, 'industry': 11, 'historical_replay': 10, 'portfolio': 28, 'valuation': 3}
- **future_leakage** (n=15, severity=high) cats={'historical_replay': 15}

## Distance to Quality Programme targets

- 1000-Q pass %: observed **88.2** / target **90.0** (gap 1.8)
- Framework selection proxy: observed **75.3** / target **98.0**

## Programme note

Every sprint must start with a measured weakness and end with a measurable improvement. IEL is the measurement system that protects AGIB from feature theatre.
