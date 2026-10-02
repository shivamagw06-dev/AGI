# Portfolio library

Public routes: `/portfolios`, `/portfolios/india`, `/portfolios/usa`, `/portfolios/:market/:id`.
Admin editor: `/admin/portfolios`.

26 USA reference portfolios and 348 disclosed holdings were captured from Vested on 2 October 2026. Source URLs and dates remain in each record. US Top10 is partial (29.60% disclosed); no undisclosed stocks are inferred. Seed symbols are blank until verified. India starts empty. Historical third-party returns are deliberately not presented as AGI returns.

`agi_portfolio_catalog` stores published documents, revisions, update timestamps and the admin actor. RLS is enabled; anon/authenticated have no grants or policies. The service-role backend alone reads/writes after API authorization. The RLS-no-policy advisory is intentional for this server-only table. No secrets enter client code.

GET `/api/portfolios` is public through the server. PUT `/api/portfolios/:id` requires the existing verified admin middleware. Weights, dates, duplicates and limits are validated. Complete portfolios total 100% ±0.05 rounding. Partial portfolios are prominently labelled. A matching revision is required for updates, including a conditional DB update to reject stale concurrent edits. Editing a reference preserves source metadata and labels it an AGI customization. Publishing is immediate, with no broker integration or automated rebalancing.

Deployment: database migration `20261002090130_portfolio_catalog.sql` has been applied to AGI Supabase and verified (26 rows, 348 holdings, RLS enabled). Frontend and backend code must both be deployed to expose pages and API. Existing single `/portfolio/*` routes remain unchanged.

Validation: `node --test server/services/portfolioCatalog.test.js`; `npm run build`. Local browser tests use the actual captured seed fixture, not production API evidence.

Local Chrome verification passed: 26 USA cards; search reduced to Genomics; details showed 11 holdings; US Top10 disclosed 70.40% missing; India empty state; 390px mobile without page-section overflow; no browser page errors. This used API fixture interception and does not confirm deployed API behavior.
