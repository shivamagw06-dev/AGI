# Financial Modelling Studio

Route: `/financial-modeling` (British-spelling alias: `/financial-modelling`).

The page contains all 16 models from the reviewed illustrative Excel library. It provides editable opening and annual inputs, independently calculated Base/Downside/Upside scenarios, five-year forecasts, KPIs, valuation measures, reconciliations and inspectable formulas. Draft inputs autosave to localStorage under the verified account ID. Named models keep up to 20 explicit versions (30 models per browser). Storage is browser-only, not cloud-synced; errors are surfaced, inputs can be backed up as JSON, and older-library drafts are retained rather than silently applied to changed cell addresses.

## Downloads and account access

`GET /api/financial-models/library` requires a bearer access token. The backend verifies the token with Supabase `getUser` and requires a non-anonymous account with confirmed email. The frontend uses the existing AGI signup/sign-in page and its `next` parameter. No auth configuration or database migration is required.

The backend needs its existing `SUPABASE_URL` and one of `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_ANON_KEY` or `SUPABASE_SERVICE_ROLE_KEY`. Keys remain on the backend. The file response has `Cache-Control: private, no-store`.

The original workbook lives under `server/assets/financial-models/`, outside Vite public assets. Hostinger root and public `.htaccess` rules deny direct access to this directory, including Git-root hosting. Preserve those rules on deployment. Do not move the workbook into `public/`.

“Download Excel library” returns the reviewed, formatted original with illustrative assumptions. “Export my model” produces a workbook with four visible sheets: Controls, the selected sector, KPI Guide and ReadMe. The latter includes the user's current inputs, formulas and recalculated result caches. Excel recalculation is requested on opening. Custom export patches the original OOXML package, preserving layout, charts, frozen panes and validation; formula and chart caches are refreshed. Unreferenced template parts remain in the package, but no other model’s user overrides are written.

## Calculation source

`server/assets/financial-models/financialModels.json` is generated from the workbook, not separately hand-entered model assumptions. The bounded interpreter supports only the formula operators and functions used by this library, never arbitrary JavaScript or uploaded formulas. Missing inputs, division by zero, cycles and invalid discount assumptions produce visible unavailable results.

Refresh the catalog and protected original together:

```sh
node scripts/extract-financial-models.mjs /absolute/path/to/reviewed-library.xlsx
node --test src/lib/financialModelEngine.test.js server/routes/financialModels.test.js
```

Review changes to the model formulas and source checksum before deploying. The tests compare every sector formula against the reviewed workbook's cached outputs, reconcile each scenario, distinguish blank from zero, validate changed annual inputs, reopen customized exports, and verify authenticated download behavior.

## Deployment

Deploy both the frontend and the Node backend using the site's existing Hostinger/Render workflows. Both the model catalog and Excel library are protected backend endpoints; both deployments are required. The server's build context must include its asset directory. No Sites project or separate hosted website was created.

Verification for the v2 upgrade: formula cache parity across all 16 models; three-case balance-sheet reconciliation; growth/claims/repayment boundaries; supporting schedules; sensitivity centers; date roll-forward; literal historical-source text; chart/validation retention; account-isolated saves; and authenticated endpoint tests. A disposable export was opened in desktop Excel without repairs, its growth input edited and recalculated, and 726 numeric formula caches matched the browser calculator. Local browser testing covered errors, reload recovery, named saves and historical inputs.

## Scope

These are illustrative business archetypes, not verified company forecasts. Company-specific accounting, regulatory capital and project schedules still need professional review. Inputs remain on the user's device; no financial figures are submitted to a backend by this page. The download request carries only the authentication token.


Access: The entire workspace, model catalog, original workbook and customized exports require a confirmed, non-anonymous AGI account. Catalog data is served from the backend only after Supabase token verification; no catalog is included in public JavaScript. The homepage contains a compact Financial Models link.

## V2 workbook

Annual valuation dates are 31 March immediately preceding the selected first forecast year (2020–2040). Changing the year relabels the annual model; the analyst must supply opening balances for that date. This is not a mid-year/stub-period DCF. Historical actuals are blank comparison inputs with source/date fields, not automatically imported or used to overwrite opening balances.

Each formerly shared annual driver has Base/Downside/Upside inputs; unchanged illustrative defaults deliberately remain equal until the analyst varies them. The original active build remains authoritative. Debt schedules expose movement timing; depreciation adds an optional current-year fraction; cash tax schedules include simplified loss carryforwards. MAT, deferred tax, tax-loss expiry, and company-specific restrictions need separate review. Existing working-capital schedules remain available under Schedules.

IT and renewables provide optional detailed operating bridges. IT separates hires, attrition, offshore mix and onsite billing. Renewables separates commissioning and operating-year fractions, construction cost and maintenance capex, with after-all-capex DSCR (not a lender-specific covenant). Real estate has an aggregate project collections/cost rollforward, not a project-by-project construction model. Operating companies have WACC/g DCF, multiple/EBITDA equity value, and revenue/margin EBITDA grids. The financial institution cases retain their book-based approach.

The website withholds valuation and customized export while material checks fail; Excel shows check warnings and retains editable formulas. Sheet protection is not enabled. The library remains illustrative, with no invented historical financials.

The upgrade builder requires the bundled artifact-tool runtime and a v1 baseline workbook/catalog (available in commit 7c75637). Pass baseline.xlsx, baseline.json and an output directory to scripts/upgrade-financial-model-library.mjs. Regenerate the catalog using the emitted metadata.json; the committed metadata is the default for subsequent extractions.
