# IDS-02 — Decision Calibration & Explainability

**Mission:** AGI no longer returns a recommendation with a single opaque confidence score. Confidence is **computed** from measurable contributors via a versioned `CalibrationProfile`.

```text
Evidence → Reasons → Decision → Calibration Engine → Institutional Report
```

No Gemini. No GPT. No phrase bank.

## CalibrationProfile (tunable, reproducible)

Weights live in the profile — not hard-coded inside the engine architecture:

```text
evidence_quality_weight
reasoning_strength_weight
valuation_certainty_weight
forecast_stability_weight
macro_stability_weight
unknown_penalty_weight
contradiction_penalty_weight
profile_version  ← stored on every decision
```

Historical decisions remain reproducible because each decision records the profile version used.

## Outputs

- Calibrated `final_confidence` (0–100)
- Positive / negative contributors, unknowns, penalties, bonuses
- Decision scorecard (Business / Financial / Valuation / Risk / Macro / Management / Evidence / Unknowns)
- Decision drift (previous → current)
- Full lineage: Evidence → Reasons → Decision → Calibration → Report

## Access

```bash
cd intelligence-engine
PYTHONPATH=. python3 -m institutional_calibration --ticker AXISBANK
```

API:

- `GET /v1/calibration/health`
- `GET /v1/decision/company/{ticker}?include_calibration=true&include_drift=true`
- `POST /v1/calibration/company`

BFF: `/api/intelligence/calibration/*` and decision query flags.

## UI

Company workspace → **Decision** tab shows recommendation, calibrated confidence, breakdown, scorecard, drift, and lineage.

## Out of scope

Phrase bank, grammar engines, LLM polish, portfolio calibration, macro calibration.
