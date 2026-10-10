# CI Acceptance Data

Production regression must evaluate AGI against the **same acceptance dataset** locally and in GitHub Actions. Without this, CI runs against empty gitignored stores and infrastructure failures masquerade as product failures.

## Problem

`intelligence-engine/data/` is gitignored. Locally you may have thousands of CapIQ rows, IKT facts, and KF objects. In GitHub Actions those directories are empty, causing suites like canonical classification to report `0/0 FAIL` instead of evaluating real companies.

## Solution

A **version-controlled acceptance corpus** at `intelligence-engine/acceptance_fixtures/` with 10 representative NIFTY companies:

| Ticker | Company |
|--------|---------|
| TCS | Tata Consultancy Services |
| INFY | Infosys |
| HDFCBANK | HDFC Bank |
| RELIANCE | Reliance Industries |
| ICICIBANK | ICICI Bank |
| ASIANPAINT | Asian Paints |
| TITAN | Titan |
| LT | Larsen & Toubro |
| MARUTI | Maruti Suzuki |
| BHARTIARTL | Bharti Airtel |

Each fixture includes:

- Valuation consensus row (company master, sector, industry)
- IKT facts (company_master, business_model, financials)
- Knowledge Factory object and pack
- Evidence pack sample
- Decision sample (where available)

## Pipeline

```text
Checkout
  ↓
Bootstrap Acceptance Data     scripts/ci/bootstrap_acceptance_data.py
  ↓
Acceptance Data Health Check  scripts/ci/check_acceptance_data.py
  ↓
Production Regression         ask_product_test.run_production_regression_v1
  ↓
Upload Reports
```

If the health check fails, regression **does not run**. Exit code **2** = infrastructure failure.

## Local usage

```bash
# Bootstrap fixtures into intelligence-engine/data/
python scripts/ci/bootstrap_acceptance_data.py

# Verify datasets
python scripts/ci/check_acceptance_data.py

# Run full gate (bootstraps automatically unless SKIP_ACCEPTANCE_BOOTSTRAP=1)
cd intelligence-engine
ASK_TEST_MODE=inprocess python3 -m ask_product_test.run_production_regression_v1
```

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | All suites passed |
| 1 | Product failure (scores below threshold) |
| 2 | Infrastructure failure (missing acceptance data) |

## Infrastructure vs product failures

**Infrastructure** (exit 2):

- Missing fixtures
- Missing valuation consensus rows
- Missing IKT companies
- Suite returns `NOT_EVALUATED` because stores are empty

**Product** (exit 1):

- Answer quality below threshold
- Founder evaluation below threshold
- Coverage policy violations
- Any suite that ran with data but failed acceptance criteria

Regression reports separate `infrastructure` and `product` sections in `artifacts/production_regression_v1.json`.

## Environment variables

| Variable | Purpose |
|----------|---------|
| `ACCEPTANCE_FIXTURES_ROOT` | Path to tracked fixtures (default: `intelligence-engine/acceptance_fixtures`) |
| `KIP_DATA_DIR` | Runtime data parent |
| `VALUATION_CONSENSUS_ROOT` | CapIQ consensus store |
| `IKT_STORE_ROOT` | Institutional knowledge tables |
| `KF_STORE_ROOT` | Knowledge Factory store |
| `IERE_STORE_ROOT` | Evidence retrieval packs |
| `SKIP_ACCEPTANCE_BOOTSTRAP` | Skip auto-bootstrap in regression runner |

## Updating fixtures

When golden company data changes materially, regenerate from a machine with full local data:

```bash
cd intelligence-engine
python3 -c "
# See acceptance_fixtures extraction in git history or run extract script
"
```

Commit changes under `intelligence-engine/acceptance_fixtures/` only — never commit full `data/` directories.

## Full universe vs acceptance corpus

| Dataset | Use |
|---------|-----|
| **Acceptance corpus** (10 companies, tracked) | CI, production release gate, deterministic regression |
| **Full universe** (5,000+ companies, local/gitignored) | Development, nightly integration, Milestone 1 compile |

This separation keeps CI fast and reproducible while allowing comprehensive local testing.
