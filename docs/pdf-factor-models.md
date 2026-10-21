# Five-factor research builder

Admin route: `/admin/factor-models`, linked from portfolio administration and protected by the existing RequireAdmin route. Input is a JSON snapshot; output is a downloadable audit and proposed long/short deciles. There is no database mutation, broker action, automatic rebalance, or overwrite of current portfolio history.

Source: India Equity Strategy, 11 October 2026, pp. 19–20. Implements Momentum, Value, Growth, Quality and All-Weather with the disclosed component weights. Universe is a dated NIFTY 500 membership list. Each complete model selects 50 stocks per side with 2% weight per stock. Monthly rebalance is the intended cadence; scheduling/execution is not implemented by this research page.

## Explicit AGI choices, not an exact proprietary replica

- Midrank percentile normalisation, with ticker order resolving ties at cutoffs.
- Sector-relative earnings yield uses within-sector percentiles.
- Lower earnings risk ranks higher.
- EPS revisions average the two percentage changes, requiring positive prior EPS, matched fiscal years and 85–95 days between observations. This tolerance is an approximation to three calendar months.
- Historical EPS growth, expected EPS growth and earnings risk require supplied methodology descriptions. A description is an audit field, not independent verification of the method.
- All 500 stocks must have complete inputs for a model before it ranks. Missing input policy is stricter than the source, whose policy is undisclosed.
- All-Weather weights the four composite scores, not the constituent portfolio holdings.

## Data contract

The UI downloads a blank template. Percentages must use percentage-point units consistently. Dates are observation dates, not export dates. The operator must reconcile constituent membership, corporate actions, forecast fiscal periods and point-in-time availability before loading. Provenance and dates are validated structurally; this is not an independent audit of vendor values. Total return fields must include distributions, not just price changes. Forward earnings yield must reflect rolling 12-month earnings. Book and sales yields must use compatible price and financial statement bases.

Trendlyne company Forecaster pages expose matched FY1/FY2 EPS and 90-day prior consensus. The bulk downloader warns that some Forecaster fields are display-only. Exact earnings-risk dispersion is still unresolved; do not manufacture it from high/low estimates. No full-universe Trendlyne snapshot is bundled or automatically scraped.

## Validation and remaining work

Tests cover weights, equal allocations, disjoint deciles, immutable input, missing risk, fiscal rollover, future observations, universe validation and revision arithmetic. Synthetic fixtures are only tests, never published portfolio results. No historical backtest, costs, performance graph or live stock recommendation is produced. Before activation: supply verified complete data, settle methodology ambiguities, validate chronological performance with costs, and apply any approved allocation through the existing dated rebalance workflow.
