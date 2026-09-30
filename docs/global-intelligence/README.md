# AGI Global Intelligence — first release

## Scope

Public route `/intelligence` and private review desk `/admin/global-intelligence`.

Two fixed public endpoints are polled server-side every 30 minutes (first attempt one minute after API startup): USGS M4.5+ seven-day GeoJSON and NASA EONET v3 events, 30 days, maximum 100 provider results. Polling does not mean a provider updates every 30 minutes. EONET latest point only: no track, polygon or hazard-footprint inference. USGS is a rolling feed, not an exhaustive earthquake archive. Results persist to Supabase; public read is the newest 300 records observed in the past 30 days. Old stored observations are retained, but revisions overwrite current facts; review audit records retain the reviewed hash and assessment, not a full raw provider archive.

Initial company directory contains 9 approximate areas across Reliance Industries, Tata Steel, Adani Ports and NTPC, supported by official company pages / FY2024–25 report. Company relationship confidence is distinct from coordinate precision and current operational status. The analyst must verify changes; no automatic refresh of company disclosures is implemented.

## Evidence flow

Source observation → 100 km point-to-point proximity candidates → analyst review → public assessment.

Proximity is not an operational-impact finding, exposure amount, hazard boundary or investment recommendation. Company pages show mapped areas and nearby observations; they do not claim a complete asset register. A new content hash invalidates previously published assessments automatically. Publishing compares the hash under a row lock and writes the review and audit together. Collectors preserve first_seen_at on provider revisions. No synthetic publication timestamps are supplied when the source omits them.

## Security and operations

- All seven new public-schema tables have RLS enabled and no anon/authenticated table privileges. Backend uses the existing Supabase service-role configuration; no new secrets.
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
| dgtlmoon/changedetection.io | Official operating-notice changes | Not connected; needs deployment, allowlist and versioned document capture |
| open-meteo/open-meteo | Asset weather context | Not connected; commercial hosted access/self-host decision needed |
| nsidc/earthaccess | NASA archive discovery | Not connected; dataset-specific access and interpretation needed |
| sentinel-hub/sentinelhub-py | Satellite imagery requests | Not connected; service account and imagery permissions needed |
| keplergl/kepler.gl | Analyst spatial exploration | Not connected; add after richer asset geometry exists |
| dgunning/edgartools | US filing evidence and entity mapping | Not connected; needs SEC identity/user-agent and extraction checks |

Next implementation order: expand verified company assets → official-document change collection → persistent event-version archive → analyst impact classifications with linked company evidence → permitted market-price overlays → client notification preferences. Do not publish auto-generated buy/sell conclusions from geography alone.

## Verification

`node --test server/services/globalIntelligence.test.js` checks source parsing, malformed and duplicate records, hash semantics, date-line distance, review validation, bounded HTTP fetches, admin denial and watchlist ownership. Production build: `npm run build`. Migration/function checks verify RLS and no anonymous function execution. Deployment smoke checks must include public read, anonymous admin denial, source freshness, globe navigation and admin queue rendering.
