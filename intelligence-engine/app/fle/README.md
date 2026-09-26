# Forecasting & Learning Engine (FLE) v1.0

Permanent institutional forecast memory, outcome tracking, calibration and continuous learning.

## Position

```text
AOI → EVE → KCV → KF → IIE → FLE → KIP → IRP → RSP → Ask AGI
```

Architecture **v1.0.1 LOCKED**. Additive only — no redesign of KF1, KCV1, AOI, EVE, IIE, KIP, IRP, RSP, or Ask AGI.

## Mission

Every forecast becomes a permanent, measurable institutional asset.

- Record predictions, assumptions, evidence, confidence
- Resolve outcomes when actuals arrive
- Measure accuracy and calibration
- Learn without overwriting history

## Invariants

- Forecasts are immutable (never overwrite; version instead)
- No forecast without assumptions
- No forecast without supporting evidence
- Learning feeds future forecasts softly — never mutates history

## APIs

`/v1/fle/health` · `/dashboard` · `/forecast` · `/company/{key}` · `/outcomes` · `/learning` · `/calibration` · `/scenarios/{id}` · `/accuracy` · `/history` · `/search` · `/consult` · `/generate` · `/batch` · `/jobs` · `/compare/{id}`

## Ask AGI

Soft field `forecast_learning` on SearchView via `FleService.consult` — retrieve forecast history and calibration **before** reasoning. Surface uncertainty when historically weak or miscalibrated.

## Out of scope (v2/v3)

Ensemble forecasting, Bayesian updates, agent competitions — not implemented in v1.
