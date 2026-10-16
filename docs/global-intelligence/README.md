# AGI Global Intelligence — first release

## Scope

Public route `/intelligence` and private review desk `/admin/global-intelligence`.

Two fixed public endpoints are polled server-side every 30 minutes (first attempt one minute after API startup): USGS M4.5+ seven-day GeoJSON and NASA EONET v3 events, 30 days, maximum 100 provider results. Polling does not mean a provider updates every 30 minutes. EONET latest point only: no track, polygon or hazard-footprint inference. USGS is a rolling feed, not an exhaustive earthquake archive. Results persist to Supabase; public read is the newest 300 records observed in the past 30 days. Old observations remain in the searchable event archive. Meaningful fact revisions are now preserved in a separate version table; unchanged polls do not create versions. Existing rows were captured as explicit archive baselines, not backfilled history.

The directory contains 14 approximate areas across 7 companies. Company relationship confidence is distinct from coordinate precision and current operational status. Seven selected official HTML evidence pages are checked daily; this is not a complete exchange disclosure feed, and linked PDFs or JavaScript-only content are not captured.

## Evidence flow

Source observation → 100 km point-to-point proximity candidates → analyst review → public assessment.

Proximity is not an operational-impact finding, exposure amount, hazard boundary or investment recommendation. Company pages show mapped areas and nearby observations; they do not claim a complete asset register. A new content hash invalidates previously published assessments automatically. Publishing compares the hash under a row lock and writes the review and audit together. Collectors preserve first_seen_at on provider revisions. No synthetic publication timestamps are supplied when the source omits them.

## Security and operations

- All Global Intelligence tables have RLS enabled and no anon/authenticated table privileges. Backend uses the existing Supabase service-role configuration; no new secrets.
- Public endpoint excludes reviewer/user identifiers and rejected assessment text. The client receives only current published reviews.
- Admin endpoints use existing verified-admin middleware. Publishing, rejection and review history record the actor; asset addition records actor/time. Asset removal deactivates its record.
- Watchlists authenticate with Supabase getUser and always write under the verified user ID. No user-supplied ownership ID is accepted. Lists are private and limited to 100 known company symbols. Removing a company asset does not erase user preferences.
- Collector URLs are fixed; admin evidence links are displayed, never fetched. Fetches reject redirects, time out at 20 seconds and cap bodies at 4 MB.
- A three-minute database lease prevents duplicate simultaneous collectors. Failed refreshes preserve prior observations and display source freshness. Admin can retry with Collect sources now; lease also applies.
- Set `GLOBAL_INTELLIGENCE_COLLECTOR=false` to disable polling. There is no independent worker: API service uptime determines collection. UI source freshness exposes outages. No backfilled alerts are sent.
- `/api/global-intelligence/snapshot` is public, with 60-second cache eligibility; authenticated responses use no-store. API rate limit 90 requests/minute/IP.
- No paid subscriptions, brokerage access or automatic orders are introduced.

## Software and remaining roadmap

Implemented globe uses **globe.gl** (MIT), topojson-client (ISC), and world-atlas country data derived from Natural Earth (public domain). The large WebGL bundle is lazy-loaded only on the map tab and falls back to the event list when unsupported. It is not a deployment of God’s Eye View or World Monitor.

| Repository | Intended use | Release status |
|---|---|---|
| bilawalsidhu/gods-eye-view | Globe interaction reference and future licensed layers | Reference only |
| koala73/worldmonitor | Geopolitical/news context | Not connected; AGPL/commercial terms review before reuse |
| OpenBB-finance/OpenBB | Normalised market/fundamental adapter | Not connected; provider redistribution rights separate |
| dgtlmoon/changedetection.io | Official operating-notice changes | Not installed; native fixed-allowlist HTML monitoring implemented for seven pages |
| open-meteo/open-meteo | Asset weather context | Not connected; commercial hosted access/self-host decision needed |
| nsidc/earthaccess | NASA archive discovery | Not connected; dataset-specific access and interpretation needed |
| sentinel-hub/sentinelhub-py | Satellite imagery requests | Not connected; service account and imagery permissions needed |
| keplergl/kepler.gl | Analyst spatial exploration | Not installed; map exports compatible GeoJSON for external exploration |
| dgunning/edgartools | US filing evidence and entity mapping | Not connected; needs SEC identity/user-agent and extraction checks |

Completed core workflow: company directory → daily evidence-page monitoring → persistent event revisions → company-linked analyst impact classifications → existing AGI stock research link → private in-app alert preferences. Broader disclosures, licensed market overlays, weather/imagery/shipping layers remain outside this release. No auto-generated buy/sell conclusions from geography.

## Verification

`node --test server/services/globalIntelligence.test.js` checks source parsing, malformed and duplicate records, hash semantics, date-line distance, review validation, bounded HTTP fetches, admin denial and watchlist ownership. Production build: `npm run build`. Migration/function checks verify RLS and no anonymous function execution. Deployment smoke checks must include public read, anonymous admin denial, source freshness, globe navigation and admin queue rendering.

## Coverage expansion — 1 October 2026

The additive company-coverage migration adds five areas across Indian Oil (IOC: Panipat, Paradip), Hindalco (Renukoot, Dahej), and JSW Steel (Vijayanagar/Toranagallu), bringing seeded coverage to seven companies / fourteen areas. Each record links to its official company location page; these are evidence of a documented relationship, not a live operating-status check. Existing analyst records are preserved on conflict.

Directory search matches company names, symbols and asset-area names. Sector filters use every mapped asset's sector; search and sector combine. Counts are derived from active records rather than hard-coded pilot numbers. Clear filters restores all active companies. Existing company pages, map markers, proximity matching and private watchlists consume these new records automatically.

Coordinate references (rounded town/area markers only): Panipat/Paradip from [GeoNames](https://www.geonames.org/search.html?country=IN&q=&startRow=450); Renukoot from [LatLong](https://www.latlong.net/place/renukoot-uttar-pradesh-india-11072.html); Toranagallu from [Wikidata](https://www.wikidata.org/wiki/Q16901850); Dahej reuses the existing approximate area marker. This does not constitute a surveyed site boundary. New company relationship sources are retained in each database record.


## Research workflows — 1 October 2026

- `/intelligence/archive`: searchable saved observations, 50 per page, maximum 100 pages; event detail loads archived records outside the rolling live feed. Event revision detail returns the newest 100 captures. A→B→A changes are retained as three versions. Archive setup creates a baseline with its real capture time.
- Admin reviews have impact type, business-impact direction, horizon and up to 20 company links. These are analyst judgments supported by the entered evidence URL, not price forecasts. The RPC locks the event, checks its current hash, and writes classifications and review audit atomically. Only published, hash-current reviews appear to clients.
- Daily page checks run inside the existing backend, once a page is due (24 hours since its last attempt), with an hourly due check and a startup check after 90 seconds. A database lease prevents concurrent batches for ten minutes. Admin can request a background batch and refresh status. Service downtime delays checks; the UI shows the last successful capture.
- Monitors fetch only seven exact URLs defined in `documents.js`. No user-entered URL is fetched. Redirects are rejected, each response has a 20-second timeout and 2 MB limit. HTML is parsed with parse5; scripts, navigation, headers, footers and forms are ignored. Latest normalised text is private; version hashes, counts and capture times are public. Only admins see short changed-text extracts. No full third-party document is republished. Baseline captures are not reported as changes.
- Official-page changes do **not** modify asset relationships or publish a business-impact assessment automatically. Formatting/content shifts can produce false positives; intra-day edits can be missed. Indian Oil returned HTTP 307 without a usable Location during initial testing; this is reported as a failed check, not bypassed or falsely marked current.
- Private inbox defaults off. Preferences use the verified session identity; no email/push dispatch is configured. Current watched companies filter nearby observations (optional, default off), current published company-linked assessments and non-baseline page changes. Only records after enabling, within 30 days, are eligible. Maximum 100 inbox items; source snapshot/document-history caps apply. Re-enabling resets the start time. Mark-read uses the displayed batch start timestamp, not a future time.
- Company pages link to the existing gated `/research/stocks/:symbol` for market context. New public market-data redistribution or causal price/event attribution is not introduced.
- Map exports only public event facts and approximate company-area markers as GeoJSON, with provenance and limitations. No private review/user fields are exported.

### Validation / deployment

Targeted tests cover fetch allowlisting/limits, parser noise/block pages, baseline/diff semantics, current-hash review checks, watchlist filtering, opt-in window, unread state, unauthenticated denial, ownership spoofing and safe spatial exports. Transactional database validation inserts temporary observations and documents, checks deduplication, A→B→A revision capture, classified audit records and stale-review rejection, then rolls everything back. No synthetic client evidence remains.

Migration: `20260930194802_global_intelligence_research_workflows.sql`. All new tables have RLS and no anon/authenticated privileges; new RPCs are service-role-only. The migration is additive and compatible with the prior app. Rollback application code without deleting captured research; disable polling with `GLOBAL_INTELLIGENCE_COLLECTOR=false` if needed.

### Remaining external dependencies

This release completes the native pilot research workflow, not every repository integration. Still needed before expansion: verified company/asset evidence at scale; permitted comprehensive disclosure/news feeds; satellite/weather/AIS service access and commercial data rights; SEC request identity for US filings; and a consented delivery provider if email/push alerts are later requested. No purchases, account registrations or paid-feed assumptions were made. World Monitor code has not been incorporated. These items should be completed after choosing providers and scope rather than represented as live coverage.
