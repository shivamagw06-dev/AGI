# AGI Institutional Reliability Roadmap

## Authority

`GET /v1/reliability/roadmap` is the acceptance authority for the four-stage
reliability programme. Individual models, scanners, forecasts and portfolio
components cannot promote themselves.

## Phase gates

| Phase | Acceptance requirement | Fail-closed state |
| --- | --- | --- |
| 1. Data Integrity | Freshness, completeness, point-in-time and corporate-action evidence pass for every registered strategy | `IN_PROGRESS` |
| 2. Validation | Every strategy reaches at least `RESEARCH_VALIDATED` through immutable registry evidence | `IN_PROGRESS` |
| 3. Forecast Intelligence | Governed outcome count, error, direction, confidence, sector and consensus gates pass | `ACCUMULATING_OUTCOMES` |
| 4. Portfolio Intelligence | Portfolio quality gates pass and at least one strategy is independently approved for production | `GOVERNED_BLOCKED` |

The overall board remains `IN_PROGRESS` and `execution_eligible=false` until all
four phases pass simultaneously. Portfolio analysis without `strategy_id` is
research-only. Supplying a strategy ID still cannot enable execution unless the
Validation Registry reports lifecycle `PRODUCTION`, health `HEALTHY`, and all
required evidence gates passed.

## Current known limitations

- Exact filing/effective dates remain incomplete for annual fundamentals.
- Corporate-action verification, historical constituents and delisted-security
  coverage remain incomplete.
- Forecast outcomes and licensed consensus vintages remain insufficient.
- Capacity, risk, parameter stability and walk-forward evidence remain incomplete
  for strategies that have only mathematical or backtest outputs.

These limitations are displayed as evidence gaps. They must never be converted
to passes by assumptions or presentation-layer labels.
