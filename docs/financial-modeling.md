# Financial Modelling Studio

Route: `/financial-modeling` (British-spelling alias: `/financial-modelling`).

The page contains all 16 models from the reviewed illustrative Excel library. It provides editable opening and annual inputs, independently calculated Base/Downside/Upside scenarios, five-year forecasts, KPIs, valuation measures, reconciliations and inspectable formulas. Input changes are held in memory. An expiring same-tab session draft preserves changes while following the sign-in flow; this is not cloud model storage.

## Downloads and account access

`GET /api/financial-models/library` requires a bearer access token. The backend verifies the token with Supabase `getUser` and requires a non-anonymous account with confirmed email. The frontend uses the existing AGI signup/sign-in page and its `next` parameter. No auth configuration or database migration is required.

The backend needs its existing `SUPABASE_URL` and one of `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_ANON_KEY` or `SUPABASE_SERVICE_ROLE_KEY`. Keys remain on the backend. The file response has `Cache-Control: private, no-store`.

The original workbook lives under `server/assets/financial-models/`, outside Vite public assets. Hostinger root and public `.htaccess` rules deny direct access to this directory, including Git-root hosting. Preserve those rules on deployment. Do not move the workbook into `public/`.

“Download Excel library” returns the reviewed, formatted original with illustrative assumptions. “Export my model” produces a smaller workbook with Controls, the selected sector, its KPI guide and methodology. The latter includes the user's current inputs, formulas and recalculated result caches. Excel recalculation is requested on opening. Custom export preserves numeric formats but is not a pixel-identical reproduction of the original workbook styling.

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

The existing checkout had unrelated changes and incomplete local dependencies. The full frontend production build passed in an isolated copy with dependencies installed from the existing package manifests. Financial model tests passed; the download endpoint test passed with the declared Express 4 and Supabase client versions in a temporary test environment. Browser visual QA was blocked by an unavailable browser security policy check. Real-account authentication has not been exercised in an automated browser.

## Scope

These are illustrative business archetypes, not verified company forecasts. Company-specific accounting, regulatory capital and project schedules still need professional review. Inputs remain on the user's device; no financial figures are submitted to a backend by this page. The download request carries only the authentication token.


Access: The entire workspace, model catalog, original workbook and customized exports require a confirmed, non-anonymous AGI account. Catalog data is served from the backend only after Supabase token verification; no catalog is included in public JavaScript. The homepage contains a compact Financial Models link.
