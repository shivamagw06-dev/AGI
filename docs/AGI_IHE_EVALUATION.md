# AGI IHE Evaluation — Phase 4 Sprint 4.3

```text
COMPANY: AGI
SPRINT: Phase 4 · Sprint 4.3 Institutional Hypothesis Evaluation
IHE: institutional-hypothesis-evaluation-v1.0.0
HQS: hqs-v1.1.0
DATE: 2026-07-28
```

## Method

- Soft-wire IHE after frozen IHG in Ask pipeline + IEL soft probe.
- Run `institutional_1000` + `cio_frozen_25` (soft).
- Compare IEL/CIO to certified + IEW/IHG baselines.
- HQS v1.1 records evaluation-layer dimensions independently of CIO.

## Results

| Metric | Frozen v3.5 | IHG soft | IHE soft |
|--------|------------:|---------:|---------:|
| IEL 1000 pass % | 99.9 | 99.9 | **99.9** |
| IEL mean | 90.24 | 90.05 | 90.05 |
| CIO-25 pass % | 100 | 100 | **100** |
| HQS mean | — | 96.75 (v1.0) | **95.85 (v1.1)** |
| HQS pass % | — | — | **100** |
| Evaluation quality (HQS) | — | — | **99.55** |
| Reasoning changed | No | No | **No** |

Note: HQS v1.1 component mix includes IHE dimensions and is not a direct numeric compare to v1.0.

## Smoke

Question: *Why did Infosys margins decline after cost inflation?*

- IHG preferred: input-cost inflation  
- IHE preferred: **same hypothesis id**, `plural: true`

## Exit gate

| Gate | Status |
|------|--------|
| Deterministic evaluation | ✓ |
| Replay / IEW / IHG / reasoning frozen | ✓ |
| LangSmith spans | ✓ |
| HQS evaluation quality high | ✓ 99.55 |
| IEL stable | ✓ 99.9% |
| CIO held | ✓ 100% |
| No forced single winner | ✓ |

## Next

Sprint **4.4 Committee Reasoning** — Bull / Base / Bear views from evaluated hypotheses.
