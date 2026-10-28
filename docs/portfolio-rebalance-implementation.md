# Dated portfolio rebalancing implementation

Requested 6 October 2026: enable dated rebalances across all India and USA portfolios and deploy.

Current verified state:
- India launch baselines and daily marks persist in agi_india_portfolio_tracking / agi_india_portfolio_marks / agi_india_daily_prices. Flat edits blocked after launch.
- Conviction Short transforms the underlying index as 200 minus NAV; categories have independent normalized histories. A rebalance must not apply this transform twice.
- Growth + Momentum is a derived private portfolio; parent edits must not silently change its recorded exposure.
- USA charts currently recompute a September 15 retrospective simulation from current weights. Freeze the current series as a labelled pre-ledger simulation, never claim a September 15 live decision record.
- USA daily collector currently uses only seed securities. New scheduled holdings must be included before execution.

Implementation acceptance criteria:
1. Atomic durable per-portfolio ledger with versioned allocations, immutable historical marks and events, optimistic concurrency.
2. Server-time-stamped admin requests; future session close only. No backdating, one pending request per portfolio, no price fabrication. Missing required old/new closes withhold execution and later dependent marks.
3. Signed units and cash conservation; short-sale proceeds cannot become extra buying power. Costs explicit, reconcile old value, turnover, cost and new value. Halt if insolvent.
4. Category-specific editing and preservation of removed category/holding histories for Conviction. Private derived portfolio remains admin-only and uses explicitly scheduled combined snapshots.
5. New-stock identity resolution via NSE master / verified Yahoo metadata. Removed holdings' data remain retained. Use market-specific calendars and completed close cutoffs.
6. India source raw closes: disclose missing automated dividends/corporate action support and prevent silent distorted returns. USA adjusted-close basis: preserve previously published marks; reconcile adjustment scale between old/new downloads.
7. Public since-launch graphs and cards use ledger performance after activation; current-allocation simulations remain separately labelled. Audit panel shows request/effective timestamps, previous/new allocations, prices, costs, status and historical stock contributions.
8. Tests for adding/removing, cash, repeated rebalances, short inverse direction, category overlap, fees, missing price, stale identity, holiday, concurrency, duplicate retries, old history immutability, auth and private visibility.
9. Deploy schema (RLS/service-role-only writes), backend, frontend, verify live and perform a rollbackable isolated test. Never execute or reset actual portfolio holdings merely to test.

Workspace branch codex/portfolio-dated-rebalances from deployed main 4d3f91a4e.
The service-role-only ledger table has been deployed. A rollback-only test verified that overwriting a published NAV is rejected. No allocations have been changed.

Validation: 24 targeted accounting, history and API access tests passed; all 26 USA baselines reproduce the existing September 15 simulation within 1e-8 percentage points. Existing India target allocations, including both Conviction portfolios, pass full-precision rebalance validation.

Operational limits: India uses raw closes and requires corporate-action/dividend review; taxes and short borrow charges are excluded. USA uses adjusted-price model units, not broker execution prices. A missing execution-day price or non-trading date leaves a rebalance pending for administrator review/cancellation. India automatic recovery is limited to seven calendar days. Category sleeves retain accumulated gains/losses rather than transferring capital between categories. Historic USA results before activation remain retrospective simulations. No cash deposits/withdrawals or automatic strategy reranking are introduced.
