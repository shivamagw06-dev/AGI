# AGI v3.5 — Release Scorecard (Frozen)

**Company:** AGI  
**Verdict: CERTIFIED**  
**ENGINEERING BASELINE FROZEN: YES**  
**Date:** 2026-07-28

## Headline

| KPI | Target | Observed | Gate |
|-----|-------:|---------:|:----:|
| IEL pass (1,025) | ≥98% | **99.9%** | ✓ |
| Framework accuracy | ≥97% | **97.76%** | ✓ |
| Historical replay | 100% | **100%** | ✓ |
| Future leakage | 0 | **0** | ✓ |
| Hallucinated evidence | 0 | **0** | ✓ |
| CIO-25 pass | 100% | **100%** | ✓ |
| Intent accuracy | 100% | 99.8% | non-blocking |

## vs PR #234

| | Before | After |
|--|-------:|------:|
| Future leakage | 15 | 0 |
| Replay historical | 73.21% | 100% |
| IEL pass | 98.44% | 99.9% |

## TIRC

Temporal Integrity Certification: **CERTIFIED** (`temporal-integrity-v1.0.0`)
