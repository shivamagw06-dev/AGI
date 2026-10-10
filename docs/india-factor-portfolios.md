# India factor portfolios — 3 October 2026

Five user-approved filtered shortlists: Momentum 22, Growth 23, Value 25, Quality 25, All-Weather 25. There are 100 unique stocks. Value also holds 2% GOLDBEES: its stock/sector caps allow only 98% equities. No stocks from the alternative 20-name proposal were substituted.

Weights use retained shortlist order, with rank-tier points 5, 4.5, 4, 3.5, 3 per five names. Constrained proportional allocation iterates stock/sector capacity; basis-point rounding respects all caps. Maximum stock 7%, maximum for source market cap below INR 10,000cr 4%, source sector 25%. Source sectors, caps and ranks are the supplied 30 September workbook; they are not certified JPM scores. Rebuild with `python3 scripts/portfolios/build_india_seeds.py <filtered.xlsx>` (openpyxl required).

Start date 5 October 2026. The server checks launch eligibility every minute in NSE hours, independently of page visits. A complete batch of positive Upstox LTPs with trade timestamps no older than 120 seconds establishes inception only on that date. Actual inception time and fixed fractional units are stored immutably. A missed launch is never backdated.

## Daily prices and charts

From 4:00 pm IST each trading day, the existing server scheduler collects Upstox V3 intraday **days/1** candles for each distinct frozen holding (101 instruments including GOLDBEES). No new paid service is provisioned. Calls are sequential, separated by 300 ms; auth/rate-limit errors stop the batch. Calendar checks reuse NSE holidays and Upstox session timings. Special sessions must also have ended before collection.

Each candle must have the requested IST date, finite positive OHLC and a valid high/low envelope. Previous-session prices are rejected. Successful individual prices persist in `agi_india_daily_prices`; missing instruments retry every five minutes after 4 pm. A restart recovers missing observations within the last seven calendar days using V3 historical daily candles. Longer outages need administrator recovery. Completed portfolio/day marks are not fetched or overwritten again by the collector. Older `legacy_intraday` marks are excluded from the new charts.

Daily composite index = sum(weight × daily close / launch price) + cash weight. Starts at 100; cumulative return = index − 100. Each portfolio point requires all its dated prices with matching instrument keys. Individual stock histories can progress even when another stock blocks the composite. Latest-change returns compare with the previous recorded point (or launch), not a claimed one-day return across missing sessions. No fabricated weekend/holiday points. Daily closes are provider candle closes, not asserted to be exchange-certified settlement prices.

Public reads are storage-only; refreshes never trigger provider calls or mutate tracking. Charts include a launch point and dated daily observations, price/index versus percentage-return modes and 1M/3M/6M/1Y/since-launch windows. Changing the window does not reset the return baseline. Before launch, an honest empty state appears. Every holding (including gold) is selectable and linked from the holdings table. Cards show composite mini-charts.

Research price returns exclude fees, taxes and dividends. Corporate-action automation and dated rebalances remain unimplemented; launched catalogue edits are blocked. Splits and demergers require review. Factor classifications are the supplied snapshot, not newly certified factor data. No broker orders.

Routes: `/portfolios/india`, `/portfolios/india/in-momentum` (and in-growth, in-value, in-quality, in-all-weather). API `/api/portfolios/india-tracking`.

Validation: tests cover the IST boundary, holiday suppression, candle-date/OHLC rejection, provider throttling and rate-limit exit, frozen-unit NAV, partial persistence and missing-only retries, read-only API behavior and idempotent completion. Live collection is pending Monday's session; no production chart points are seeded for testing.

## Preferred

`in-preferred` is a separate 17-stock research portfolio from the supplied preferred-picks list, not the broader OW universe or a factor replica. Seed: `server/data/indiaPreferredPortfolio.json`. Approximately equal weights total 100%; four 5.89% and thirteen 5.88% positions. Financials total 35.31%, so the five factor portfolios’ 25% sector cap does not apply. All 17 tickers matched the Upstox NSE EQ instrument master when prepared. Shares and chart tracking use the same 5 October launch and 4 pm daily collection. Existing five allocations are unchanged.
