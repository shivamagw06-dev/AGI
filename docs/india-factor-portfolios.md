# India factor portfolios — 3 October 2026

Five user-approved filtered shortlists: Momentum 22, Growth 23, Value 25, Quality 25, All-Weather 25. There are 100 unique stocks. Value also holds 2% GOLDBEES: its stock/sector caps allow only 98% equities. No stocks from the alternative 20-name proposal were substituted.

Weights use retained shortlist order, with rank-tier points 5, 4.5, 4, 3.5, 3 per five names. Constrained proportional allocation iterates stock/sector capacity; basis-point rounding respects all caps. Maximum stock 7%, maximum for source market cap below INR 10,000cr 4%, source sector 25%. Source sectors, caps and ranks are the supplied 30 September workbook; they are not certified JPM scores. Rebuild with `python3 scripts/portfolios/build_india_seeds.py <filtered.xlsx>` (openpyxl required).

Start date 5 October 2026. Server scheduler runs every minute in weekday NSE hours and is independent of page visits. Only a complete set of positive Upstox LTPs with trade timestamps <=120 seconds old can establish inception during that date's session. Actual inception time is stored. If launch is missed, it reports this rather than backdating. Tokens are server-side. Public endpoint shares a 30-second quote cache. No new Render service or broker orders.

The inception table is immutable to the service role; latest complete session NAV is recorded separately. Missing/stale prices retain the last recorded valuation with its time. Inception weights become fixed fractional units; returns are price-only, before fees and taxes. Daily marks are last observed fresh valuations, not official closes. Corporate-action/dividend automation and dated rebalances are not implemented. Catalogue editing after inception is blocked rather than silently rewriting the record. Live market verification remains pending until an open session.

Routes: `/portfolios/india`, `/portfolios/india/in-momentum` (and in-growth, in-value, in-quality, in-all-weather). API `/api/portfolios/india-tracking`.
