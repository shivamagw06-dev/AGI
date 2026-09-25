# Wealth & Opportunity Intelligence — first implementation

Route: `/wealth-intelligence`. Entry points: the shared header's More menu (and mobile menu) and Portfolio Intelligence. Both the frontend route and `/api/wealth/universe` require sign-in. Source branch: `codex/wealth-opportunity-intelligence`.

## Repository audit

Inspected against main `fca68fdc933eeae6a0463d47d077785cce300717`.

| Capability found | Existing code | Use in this release |
| --- | --- | --- |
| Upstox V3 streaming, synchronized snapshots and freshness checks | `server/services/upstoxMarketFeedV3.js`, `liveAlphaRuntime.js` | Read existing `getLiveAlphaMarketSnapshot`; no extra sockets, subscriptions, credentials or order calls |
| Nifty 500 instrument universe, sector and ISIN mapping | `indices/Nifty500.csv`, `loadLiveAlphaUniverse` | Search and paginate current configured equity universe; company names from existing CSV |
| Upstox statements, ratios, corporate actions, historical candles, flows and calendar | `server/providers/upstox.js` and corresponding refresh services | Retained; company links open existing research. This release does not derive suitability scores from them |
| Groww and Yahoo price/history providers | `server/providers/groww.js`, Yahoo providers, `portfolioMarketService.js` | Existing functionality retained; this screen labels the shared runtime's actual source |
| Portfolio analytics, CAS import, multi-asset holdings | `src/pages/ClientPortfolioIntelligence.jsx`, `intelligence-engine/portfolio_import` | Linked from workspace; no private holdings automatically imported into assumptions |
| Founder-specific AMFI resolver | `intelligence-engine/app/founder_portfolio/providers.py` | Existing per-holding Python resolver retained. New Express directory search supplies daily scheme discovery without depending on founder holdings |
| Legacy wealth screen | `src/components/OnePageWealthTools.jsx` | Not reused: sample holdings/macro figures and simplified tax recommendations are unsuitable for this product |
| Direct land listings / local transaction comparables | No integrated source found in audited provider paths | Manual evidence form only; no fabricated locality rankings |
| Executable bond offerings / current bank deposit catalogue | No integrated source found in audited provider paths | Explicit coverage gap; manual scenario assumptions |

Read-only production verification on 24 September 2026: the existing `/api/market/live-alpha/status` reported `provider=upstox`, feed `connected`, 500 universe members and 721 subscribed instruments. This confirms the runtime status at inspection, not entitlement to every asset class or freshness of every quote.

## Delivered workflow

1. Enter capital, whole-year horizon, FD benchmark, effective income-tax assumption and inflation. Initial numbers are generic examples, not a stored family profile.
2. Search companies/sectors from the configured Upstox universe or fund names/houses/categories from AMFI.
3. Every quote carries its real source and observation time. Missing prices remain null. Stale data never receives a Live label. Fund NAVs are daily, never intraday.
4. Add up to four scenarios with separate price growth, cash income, entry/exit costs, holding costs and effective exit gains tax. Edit or remove scenarios.
5. Compare first-year income, net exit wealth, total taxes/costs, inflation-adjusted wealth and differences against the FD. View an annual path and download the complete inputs/results as JSON.
6. For property, record location, asking/registered/guidance/estimated price evidence, source, evidence date and document-review status. Show required annual appreciation to match the FD and any whole-property budget shortfall.

## Data contracts and operations

`GET /api/wealth/universe?assetClass=equity|mutual_fund&q=...&offset=0&limit=25`

- Validated bounded search/pagination. Server verifies bearer token with Supabase `auth.getUser`, rejects anonymous users, and returns `private, no-store`.
- `items`: identifier, name, asset class, price, source, observation date, freshness status and research link where supported.
- `source`: provider/runtime status; transport fetch time is distinct from quote/NAV observation date.
- Equity page refreshes every 30 seconds; fund page every five minutes. AMFI origin fetch cached one hour across clients, with coalesced requests, 12-second timeout and one-minute backoff on failure.
- AMFI adapter supports both six-column legacy records and the eight-column layout with separate Plan and Option. Rejects invalid prices/dates and reports stale cache explicitly.
- Equity freshness requires existing runtime `PASS` plus a valid non-future timestamp no older than two minutes. NAVs older than four calendar days are marked stale (a conservative flag, not a trading-calendar guarantee).
- No additional Upstox secrets. Existing server Supabase credentials are needed for authentication. Outbound access to `https://portal.amfiindia.com/spages/NAVAll.txt` is needed for the NAV directory.
- No schema migration, broker execution, persistent client financial storage, additional AI provider or paid data subscription is introduced.

## Financial model

This is an unlevered nominal scenario model, **not a statutory tax calculator**. All rates are supplied by the user. There are no preset market return forecasts or product tax classifications.

For budget `C`, entry cost `e`, asset value begins at `C / (1 + e)`. Each year, cash distributions and holding costs are based on opening value; price grows by the specified rate. Positive cash either earns the assumed net FD rate or remains at zero return. It is not assumed spent. Negative cash is disclosed as external funding required and does not earn interest.

On a hypothetical exit each year, deduct selling costs and the assumed tax on positive gains above `C`, then add accumulated net cash. All entry costs enter tax basis as an explicit simplifying assumption. No credits on losses, holding-cost deduction, surcharge calculation, exemptions, indexation, debt, rate changes, stamp-duty valuation rules or transaction-level timing are modelled. Cash balances earning FD interest also pay the assumed income tax. Annualized growth is the final-wealth CAGR, not a distribution IRR.

The property quote is recorded evidence; it does not silently change the common capital budget. Comparisons represent an exposure sized to that budget, not proof that a specific indivisible plot can be purchased. The UI states this and flags quote-plus-entry-cost shortfalls. Exact-property funding and residual-capital allocation belong in the next release.

## Validation performed

- 19 focused tests passed initially: independent FD formulas, no-reinvestment cash, property entry/exit costs, break-even inversion, losses, funding shortfalls, invalid inputs, AMFI schema/caching failures, quote/NAV freshness, server authentication and route gating.
- `npm run build` passed.
- Live AMFI fetch and parser succeeded: 14,155 usable scheme records observed on 24 September 2026. Counts change with the source.
- Local equity service loaded 500 existing members and truthfully reported unavailable quotes without deployment credentials.
- Browser visual QA remains outstanding: the available remote browser rejected the local preview with `ERR_BLOCKED_BY_CLIENT`. No browser pass is claimed.
- Production login and end-to-end authenticated requests for the new route require a deployed review environment; not verified in this session.

Focused command:

```sh
node --test src/lib/wealthScenario.test.js src/lib/accessPolicy.test.js server/providers/amfiNav.test.js server/services/wealthIntelligence.test.js server/routes/wealthIntelligence.test.js
```

## Next implementation increments

1. **Real property evidence:** select 2–3 pilot markets; contract a reusable listing/comparables source; normalize parcel identity, units and price type; add verified infrastructure milestones, data dates and legal-review references. Require sufficient comparable evidence before ranking an area.
2. **Instrument research:** add AMFI historical NAVs and AMC costs/holdings; connect bond terms, credit history and executable quotes; bring existing fundamentals into transparent screens. Price alone never determines expected return or a buy recommendation.
3. **CA-reviewed tax rules:** version by effective period, taxpayer and residency; support ownership, capital-gains lots, surcharge/cess, deductions, losses and documented eligibility. Review 1961/2025 Act transition mappings rather than recycling old section numbers.
4. **Household planning:** explicit owner-level portfolios, income needs, liquidity reserves, debt, concentration and financing. Add private persistence only with consent and ownership policies.
5. **Monitoring:** saved comparisons, dated rules and evidence-change alerts. Keep data quality separate from investment attractiveness and suitability.

Merge/deployment follows existing repository gates and production workflows. This branch does not directly publish or merge to main.

## Second increment: household and evidence workspaces

Added six working panels on the existing signed-in route:

- **Household:** legal owners (individual/HUF/business), residency, owner-specific tax inputs, holdings, debt, gross cash income, geography, concentration, spending and reserve targets. Joint holdings must be split into ownership shares. No actual family figures are preloaded.
- **Fund research:** dated AMC evidence, scheme codes, expenses, risk labels and disclosure-weight overlap, with partial-coverage and mismatched-date warnings. No performance history or manager-change feed is claimed.
- **Property evidence:** typed asking/registered/guidance/estimated observations, sq-ft normalization, micro-market/type/price-type group medians and ranges, rental yields, infrastructure stages and legal-review status. Compare action opens the FD workbench. These are supplied comparables, not an automated appraisal or verified listing service.
- **Fixed income:** explicit settlement, all-in purchase cost, principal redemption, dated coupon schedule and separate effective tax assumptions. Outputs scheduled after-tax receipts, dated IRR and annual maturity/cash-flow ladder. No assumed reinvestment, default prediction, early exercise or executable dealer quote.
- **Tax review:** deterministic ordinary-income calculator for resident individuals, FY 2025–26 / AY 2026–27, including old-regime age thresholds, rebate, new-regime rebate marginal relief, surcharge marginal relief, cess and credits. Inputs are already-computed taxable ordinary income. No deductions are inferred from gross income. Capital gains, dividends, foreign income, losses, other entities and residency cases are blocked. Tax Year 2026–27 is explicitly blocked pending separate authoritative rule verification. All outputs still require professional review.
- **Monitoring:** due/past-due maturities, stale saved market observations, stale fund/property/bond evidence, concentration and dated review tasks. Recomputed on workspace changes or user refresh; not a persistent background notification service.

Review packs include the input records, rule version, assumptions, recomputed results and current alerts. JSON export/import is explicit. Files are capped at 2 MB; collections, field sizes, dates, identifiers, URLs and ownership references are validated. Unknown workspace fields are dropped. Inputs stay in component memory and are lost when the page is left or refreshed. No financial data is written to shared browser storage or a database.

### Existing company research integration

`GET /api/wealth/research/:symbol` reads the existing **stored** five-year valuation company pack using `readLatestValuationCompanyPack`. It returns only meaningful finite metrics and preserves generation/source dates. It does not invoke an engine refresh, scan the universe, create market subscriptions or mutate Supabase. Missing research returns unavailable; stale or future-dated packs cannot be labelled available. Individual metric units/reference methods remain in the full company-research page.

`GET /api/wealth/evidence` reads a deployment-configured evidence file via `WEALTH_EVIDENCE_FILE`. Both new endpoints use the existing server-verified authentication boundary, private/no-store responses, sanitized errors and a 120 requests/minute per-IP limit after authentication. The source filename and service credentials are never returned. Client requests cannot supply a filesystem path or remote fetch URL.

### Connecting reviewed external evidence

The adapter is implemented; **no property/bond/disclosure provider is configured by this change**. A provider agreement, suitable geographic coverage, permitted redistribution and an ingestion job must be established before serving a real catalogue.

The deployment's ingestion job should atomically replace a UTF-8 JSON file with this envelope:

```json
{
  "version": "agi-wealth-evidence-v1",
  "provider": "Name of contracted or permitted source",
  "displayRightsConfirmed": true,
  "reviewedAt": "YYYY-MM-DD",
  "records": []
}
```

Each record uses `kind` (`funds`, `properties`, `bonds`, `events`) plus the exact corresponding schema in `src/lib/wealthWorkspace.js`. Required fields include a stable `id`, descriptive `name`, HTTPS `source`, and dated evidence (`asOf`) or a task due date. Numeric strings or numbers are accepted by the input normalizer. Dates are strictly validated. Provider review must be within 90 days. Maximum file size: 2 MB; maximum records: 1,000; one process-wide 60-second cache with in-flight request deduplication. Malformed/oversized/unreviewed files fail closed and serve no records. A provider declaration does not confer legal or investment approval.

Records can be added individually to the client's evidence book, including stale records with explicit warnings. The UI does not silently overwrite client research. The feed is not for client-private financial records. No broker scraping, exchange redistribution or paid subscription is enabled automatically.

### Required work before a full live launch

1. Complete deployed visual and authenticated end-to-end QA. The cloud browser did not complete the local preview check; no UI pass is claimed.
2. Obtain independent CA validation and a supported Tax Year 2026–27 package. Broader tax features (deductions, capital-gain tax lots, exemptions, loss set-offs, foreign income, HUF/business and GST) remain outside this calculator.
3. Connect permitted AMC holdings/performance, verified property transactions/availability and executable bond/bank rate feeds. This code does not fabricate them.
4. Add consented owner-isolated persistence before scheduled background monitoring or notifications. Current monitoring is session-only.
5. Complete existing CI gates and review before merging/deployment. This increment itself does not publish to production.

### Verification for this increment

40 focused and regression tests pass across financial models, evidence validation, API authentication, stale-data handling and existing institutional safety gates. Targeted no-undefined-identifier lint and production build pass. Live Supabase research reads and real vendor feed availability are not verified from this development session. No database migration, secret, market subscription or production setting changes.

## CA report and import hardening

The workspace now offers **Download CA report** (offline printable HTML, suitable for browser Print to PDF) alongside **Save editable pack** (JSON). The report includes household totals, all scenario inputs and outcomes, source observations, property comparable summaries, bond maturity cash flows, owner-level tax estimates, review tasks and source records, plus a reviewer sign-off area. It is not a signed professional opinion.

`wealthReviewPack.js` supplies a shared import/export validator. It rejects malformed nested objects, duplicate/reserved scenario IDs, invalid dates and non-boolean reinvestment settings; normalizes numeric inputs; drops unrecognized fields; and recomputes outputs instead of trusting saved totals. Watchlist records reject duplicate IDs and impossible calendar dates. Record fields reject arrays/objects instead of coercing them into visible text. Export errors are shown in the workspace.

The report escapes user text, uses no scripts or external resources, and has a restrictive Content Security Policy. No report is uploaded or sent to a reviewer automatically. Automated report-content/security tests pass; visual print pagination and deployed authenticated UI QA remain outstanding. The expanded suite has 44 passing tests. The prior implementation commit passed all three GitHub workflows; checks run again for this increment.
