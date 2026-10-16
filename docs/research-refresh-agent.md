# Research refresh agent

Admin page: `/admin/research-refresh`. Admin API: `/api/intelligence/research-refresh`.

This is a backend service, not a ChatGPT automation. It reuses the existing Node service and database; no new paid worker is required. The process checks due work every 15 minutes. A successful refresh makes the next run due **15 calendar days after completion at 17:00 IST**, not on the 1st/15th of a month. Failed or blocked runs retry after one day at 17:00 IST. Scheduled runs wait until 17:00 IST; explicit admin checks may run earlier. Database leases prevent concurrent replicas from duplicating work. Restarted workers recover expired leases. The schedule begins disabled.

## Implemented scope and limits

* Five screener exports are parsed through the existing production validators. All five and both India investor-directory scopes must validate before publication begins. Source dates, pagination counts, duplicates and large coverage drops are checked. Older published data is never replaced by an older source date.
* Directory publication uses the existing institutions preview/publish workflow. **This does not refresh every investor's individual holding-detail page.** That separate collector remains a missing adapter.
* Current five factor portfolios receive holding-level eligibility reports. Missing values never become zero. Recommendation counts are not used as earnings-estimate contributor counts. Stale figures are not exit evidence.
* **No automatic portfolio allocation changes.** Original factor ranks, liquidity checks and corporate-action reconciliation are not available from the current imports. Reports label these limitations. Use the existing dated-rebalance page for a reviewed allocation, preserving historical NAV.
* Reports record source hash, collection time, per-dataset publication results, additions/removals and blockers. A failure after one dataset is published is `partial`; earlier successful writes are reported. Retries compare the latest rows/date to avoid duplicate snapshots. The seven writes are not one cross-service transaction.

## Required one-time source connection

There is currently **no verified Trendlyne server API entitlement or authenticated automated export connection** in this repository. The service does not pretend a personal Chrome login is available on Render. Configure `RESEARCH_REFRESH_FEED_URL` to an approved HTTPS export adapter producing the contract below; optional `RESEARCH_REFRESH_FEED_TOKEN` is server-only. Do not put tokens in URLs. The reader refuses redirects, HTML/login pages and responses exceeding 15 MB, with a 60-second request timeout. This is an AGI adapter contract, **not a claimed Trendlyne endpoint**.

An authorized export adapter must gather every page, retain genuine source dates, and emit data in existing downloaded-table formats. Use only access approved for automated collection and publication. If Trendlyne requires interactive sign-in/OTP or only supplies desktop exports, unattended collection remains blocked until a supported connection is provided. Exporting the file manually is a recovery path, not autonomous source acquisition.

```json
{
  "version": 1,
  "provider": "trendlyne",
  "complete": true,
  "collectedAt": "2026-10-15T12:00:00Z",
  "screeners": [
    {"slug":"momentum","asOf":"2026-10-15","complete":true,"expectedRows":19,"tables":["complete CSV including header"]}
  ],
  "institutions": [
    {"country":"IN","category":"individual","asOf":"2026-09-30","complete":true,"expectedRows":100,"text":"complete directory CSV"},
    {"country":"IN","category":"institutional","asOf":"2026-09-30","complete":true,"expectedRows":100,"text":"complete directory CSV"}
  ],
  "factorInputs":{"rows":[
    {"symbol":"EXAMPLE","asOf":"2026-10-15","marketCapCr":10000,"forwardEPS":10,"forwardPE":20,"estimateContributors":7,"corporateActionsVerified":true}
  ]}
}
```

The example is abbreviated: `screeners` must contain exactly `momentum`, `low-pe`, `piotroski`, `cash-flow`, `promoter-holdings`. Expected rows must match actual parsed rows. Factor fields must be actual numbers, not numeric strings or invented estimates. The collection timestamp must be within three days; price-based screen dates within four days. Ownership disclosure dates may be older and are never relabelled to collection day. Zero-row screens require explicit manual handling; this version conservatively blocks them rather than wiping a public list.

## Installation and verification

1. Apply `supabase/migrations/20261015120837_research_refresh_agent.sql` using the normal migration deployment process. Tables and RPCs are service-role-only with RLS enabled. Browser/admin users use the guarded backend routes.
2. Deploy backend and frontend. Navigation includes Research update agent.
3. Connect and validate the approved source adapter. Run check now; inspect all seven data outcomes and the explicit detail/ranking blockers. The system must not be advertised as full unattended coverage until those adapters are supplied.
4. Enable the schedule in the admin panel. Pause there at any time. No ChatGPT thread needs to stay open. Reports stay in the database.
5. Verify live read/write behaviour in staging and inspect database advisors before production activation. Unit tests are not proof the production migration or feed is configured.

There is no broker order path in this agent and no automatic purchase of external services. Local tests use synthetic fixtures only; they do not publish test data.

## Browser collector (implemented, live mappings pending)

Set `RESEARCH_REFRESH_SOURCE=browser` to use the new Playwright collector instead of the HTTPS feed. This adapter consumes rendered HTML tables using **explicitly verified** selectors, not undocumented private endpoints. It supports paginated screener and investor-directory tables. It does not yet download XLSX exports, ingest individual investor detail pages, or create missing factor inputs. Browser collection remains unverified on Trendlyne until the live mapping test succeeds. Do not call this complete autonomous coverage.

### Installation and private login

1. Install server dependencies (`npm ci`), then install the matching Chromium browser and system libraries (`npx playwright install --with-deps chromium`) in the collector runtime. Budget memory separately before enabling it in a busy web process; no additional Render service is provisioned by this change.
2. On a trusted workstation set `TRENDLYNE_BROWSER_STATE_PATH` to a private file **outside the repository and web document root**, then run `node collectors/trendlyneSession.js` from `server/`. Sign in directly in the dedicated browser. Complete OTP yourself. Press Enter only after successful sign-in. This does not inspect or copy your existing Chrome profile.
3. Transfer this sensitive session file through the deployment secret-file mechanism, never through chat, git, a public bucket or a public API. The runtime copy must have owner-only permissions (`0600`). Session persistence is not guaranteed across providers/IP changes. A rejected session requires reauthentication; no CAPTCHA bypass, stealth mode or proxy rotation is implemented.
4. Set `TRENDLYNE_BROWSER_MANIFEST_PATH` to a private JSON configuration. It must have `version:1`, `verified:true`, and `datasets` containing the five screener IDs plus both India investor directories. First verify each selector and whole-table schema in a real logged-in page. Never mark an untested mapping verified.
5. Each dataset requires `id`, `kind` (`screener` or `institution_directory`), exact `url`, `readySelector` proving the intended authenticated view, `tableSelector`, ordered `headers`, `keyColumn` (stable unique ID column), `dateSelector`, anchored `datePattern` capturing an actual ISO source date in group 1, `countSelector`, anchored `countPattern` capturing the total in group 1, and either `nextSelector` or `singlePage:true`. Institution entries also require `country` and `category`. If the source has no reliable date/count or isn't an HTML table, a dedicated adapter is required; don't substitute today's date or visible-row counts.
6. Run a controlled check and reconcile every row against an export before enabling the schedule. Existing publication validators still apply. The collector blocks duplicate/repeated pages, schema changes, changing dates/counts, missing pagination and totals that do not match. Rate limits and login challenges stop the run. Each collection has a ten-minute limit and at most 100 pages per dataset.

Reports show a controlled error code without dumping browser errors or session state. Completed exports are held in memory until all datasets validate; incomplete runs are re-collected, not resumed from stale pages. The existing durable run report records failures. No outbound email notification service is configured. The collector never changes portfolio allocations.

### Remaining activation work

At implementation time browser control failed before reaching Trendlyne, so **no real selectors or authenticated session were captured**. Live collection, runtime Chromium installation, approved source usage, and page mapping are required before enabling production. This code is tested against synthetic tables and failure cases only.
