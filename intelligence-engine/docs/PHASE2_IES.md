# Institutional Evaluation Suite (IES)

AGIB’s institutional-finance benchmark — the Phase 2 exit gate before Phase 3.

Not 500 random questions. Seven scored suites × 100 gold-labelled cases = **700**.

## Suites

| Suite | N | Measures |
| --- | ---: | --- |
| Valuation | 100 | Framework execution, history/peer coverage, unsupported claims |
| Business Quality | 100 | ROIC / margins / capital allocation; no unsupported “great company” |
| Accounting | 100 | Accounting framework or transparent insufficient |
| Comparison | 100 | Left-to-right entity resolution, peer selection, relative valuation |
| Insufficient Evidence | 100 | **100% transparency** — never “best guess” |
| Edge Cases | 100 | Wrong entity, placeholder, stale, negative PE, index DCF |
| Educational | 100 | Academy path — **no evidence contracts** |

## Phase 2 Definition of Done

| Category | Target |
| --- | ---: |
| Overall benchmark | ≥90% |
| Valuation | ≥95% |
| Business quality | ≥90% |
| Accounting | ≥90% |
| Comparison | ≥90% |
| Insufficient-evidence handling | **100%** |
| Unsupported conclusions | **0** |
| Editorial violations | **0** |
| Wrong entity execution | **0** |
| Evidence provenance | **100%** (when required) |
| Framework execution (valuation) | >95% |

## Run

```bash
cd intelligence-engine

# Full 700 (Phase 2 exit)
python3 -c "from institutional_reasoning.ies.production import run_ies; r=run_ies(); print(r['dashboard_text'])"

# CI sample
python3 -m pytest tests/test_ies_phase2.py -q
```

## Soft-wire

`institutional_reasoning/ies/` — not a new top-level engine.

Uses Phase 1 governance + Phase 2 institutional evidence packs.

## Latest full run (local)

```
Overall Score                 100.0%
Valuation                     100.0%
Business quality              100.0%
Accounting                    100.0%
Comparison                    100.0%
Insufficient                  100.0%
Edge cases                    100.0%
Education                     100.0%
Unsupported conclusions       0
Editorial violations          0
Phase 2 Exit Gate             PASS
```

## Maturity note

IES verifies **governance + evidence + framework execution**. Continuous learning from outcomes (prediction → realised return feedback) remains Phase 7+ and is intentionally out of scope here.
