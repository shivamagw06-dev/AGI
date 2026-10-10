# Portfolio library

Public routes: `/portfolios`, `/portfolios/india`, `/portfolios/usa`, `/portfolios/:market/:id`.
Admin editor: `/admin/portfolios`.

26 USA reference portfolios and 348 disclosed holdings were captured from Vested on 2 October 2026. Source URLs and dates remain in each record. US Top10 is partial (29.60% disclosed); no undisclosed stocks are inferred. Seed symbols are blank until verified. India starts empty. Historical third-party returns are deliberately not presented as AGI returns.

`agi_portfolio_catalog` stores published documents, revisions, update timestamps and the admin actor. RLS is enabled; anon/authenticated have no grants or policies. The service-role backend alone reads/writes after API authorization. The RLS-no-policy advisory is intentional for this server-only table. No secrets enter client code.

GET `/api/portfolios` is public through the server. PUT `/api/portfolios/:id` requires the existing verified admin middleware. Weights, dates, duplicates and limits are validated. Complete portfolios total 100% ±0.05 rounding. Partial portfolios are prominently labelled. A matching revision is required for updates, including a conditional DB update to reject stale concurrent edits. Editing a reference preserves source metadata and labels it an AGI customization. Publishing is immediate, with no broker integration or automated rebalancing.

Deployment: database migration `20261002090130_portfolio_catalog.sql` has been applied to AGI Supabase and verified (26 rows, 348 holdings, RLS enabled). Frontend and backend code must both be deployed to expose pages and API. Existing single `/portfolio/*` routes remain unchanged.

Validation: `node --test server/services/portfolioCatalog.test.js`; `npm run build`. Local browser tests use the actual captured seed fixture, not production API evidence.

Local Chrome verification passed: 26 USA cards; search reduced to Genomics; details showed 11 holdings; US Top10 disclosed 70.40% missing; India empty state; 390px mobile without page-section overflow; no browser page errors. This used API fixture interception and does not confirm deployed API behavior.

## Historical simulations (2 October 2026)

Portfolio details now load `/data/portfolio-history.json` and calculate 1/3/6/12 calendar-month current-weight buy-and-hold simulations. These are explicitly NOT Vested/AGI fund track records. Snapshot as of 1 October 2026: 300 USD security histories (holdings, research candidates and SPY calendar). No fees/taxes/INR FX, no periodic rebalancing. See `scripts/portfolio-history/README.md` for manual refresh and evidence handling. Ticker mappings do not overwrite DB holdings. Four ambiguous legacy/share-class names remain blocked pending source verification; IPO history and US Top10 incompleteness also withhold relevant results. No automatic refresh has been installed.

Complete snapshot simulations: 20/26 at 1 month and 3 months, 19 at 6 months, 18 at 12 months. `/research/portfolio-performance.html` contains the comparison with dates/gaps; `/data/portfolio-performance-summary.json` is its result evidence. Detail pages calculate using current catalog weights, so subsequent edits can differ from the dated comparison report. Component test used downloaded Yahoo prices and captured catalog locally, not invented returns. Unit tests exercise weighted returns, daily drawdown, missing observations, partial weights, share mapping mismatch and rounding.
