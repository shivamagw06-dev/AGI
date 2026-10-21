# AGI Ask Product Test Suite (Founder Acceptance)

## What it is

Product-level validation for AGI Ask — not routing-only, PAT stubs, or UI file smoke.

```bash
Browser/API → POST /api/ui/search → UiService.search → Response pack
```

## Files

| Path | Role |
|------|------|
| `intelligence-engine/ask_product_test/` | Harness, checks, fixtures, prompts |
| `intelligence-engine/tests/test_ask_product_smoke.py` | Tier A (8 prompts) |
| `intelligence-engine/tests/test_ask_product_regression.py` | Tier B (CIO-25 + isolation + determinism) |
| `intelligence-engine/tests/test_ask_product_ikl.py` | Tier IKL (5 founder memory prompts) |
| `artifacts/ask_test_report.json` | Per-question metrics after each run |
| `artifacts/ask_test_report_ikl.json` | IKL suite report |
| `artifacts/ask_test_report_pre_ikl.json` | Live baseline before IKL deploy |

## Modes

| `ASK_TEST_MODE` | Behavior |
|-----------------|----------|
| `contract` (default) | Deterministic SearchView fixtures — CI-safe product-contract gate |
| `inprocess` | Real `UiService.search` (slow; local engine) |
| `live` | `POST {ASK_TEST_BASE}/api/ui/search` — founder live gate |

## Commands

```bash
cd intelligence-engine

# CI / default — contract mode
pytest tests/test_ask_product_smoke.py tests/test_ask_product_regression.py -q

# Founder live acceptance against Render gateway
ASK_TEST_MODE=live \
ASK_TEST_BASE=https://finance-news-backend-19i5.onrender.com \
  pytest tests/test_ask_product_smoke.py tests/test_ask_product_regression.py -q

# Sample regression
ASK_TEST_REGRESSION_LIMIT=5 pytest tests/test_ask_product_regression.py -q

# Tier IKL — persistent memory validation (contract)
pytest tests/test_ask_product_ikl.py -q

# Tier IKL live after #437 deploy (strict memory asserts)
ASK_TEST_MODE=live \
ASK_TEST_BASE=https://finance-news-backend-19i5.onrender.com \
ASK_TEST_IKL_STRICT=1 \
  pytest tests/test_ask_product_ikl.py -q
```

## Pre / post IKL baseline

1. **Before merging/deploying IKL** — run Tier A+B live and save the report:

```bash
ASK_TEST_MODE=live \
ASK_TEST_BASE=https://finance-news-backend-19i5.onrender.com \
  pytest tests/test_ask_product_smoke.py tests/test_ask_product_regression.py -q
cp artifacts/ask_test_report.json artifacts/ask_test_report_pre_ikl.json
```

2. **After deploy** — re-run the same suite + Tier IKL (strict) and compare `comparison_metrics`:

| Metric | Field |
|--------|--------|
| Pass rate | `pass_rate` |
| Avg latency | `average_latency_ms` |
| Entity confidence | `comparison_metrics.avg_entity_confidence` |
| Funnel | `avg_funnel_retrieved/ranked/passed/referenced` |
| Utilization | per-question `utilization` |
| Executive attribution | `comparison_metrics.executive_attribution` |
| Fallback rate | `comparison_metrics.fallback_rate` |
| Company / industry / macro memory hits | `*_memory_hits` |

## Gates

- Tier A: **100%** pass
- Tier B: **≥ 95%** pass
- Tier IKL (contract / `ASK_TEST_IKL_STRICT=1`): **100%** pass
- Tier IKL (live soft, pre-deploy): product contract ≥ **80%**; memory misses recorded in `ikl_meta`
- No recommendation-policy violations
- No HTML/502-shaped crashes (structured degraded JSON allowed)
- Report artifact written every run
