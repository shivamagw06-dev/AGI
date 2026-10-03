# Website analytics

Admin dashboard: `/admin/website-analytics`. Central first-party tracking begins at deployment; no historical traffic is invented or imported.

The browser sends page views on pathname changes, successful model-download actions, and existing sign-up-completion events. Query strings/fragments, emails and IP addresses are not retained. Private portfolio paths are reduced to `/portfolio`; admin/account/auth/API paths are excluded. Browser IDs expire after 90 days; sessions renew after 30 minutes of inactivity. DNT, GPC and the Privacy Policy opt-out disable collection. Collection is production-host only and must never interrupt navigation or downloads.

The public event endpoint validates origin, rate-limits requests and filters basic bot user agents. Events are still browser-reported and are not fraud-proof or audited account/download totals. Sign-up event IDs deduplicate repeated callbacks per browser ID.

Summaries require the existing server-verified administrator allowlist. Engine endpoints require the service token. Events live in the separate `website_analytics.sqlite3` under the existing durable warehouse storage directory, not a public warehouse workbook tab. Production's `/v1/kip/integrity` was checked to confirm its mounted durable `/var/data/kip` disk before deployment. Include this database in disk backups. The dashboard supports 1/7/30/90 IST calendar-day windows and caps a request at 50,000 events; larger reports return an explicit error requesting a shorter range rather than silently truncating results.

Visitors = distinct browser IDs with page views in the selected range; visits = distinct browser/session pairs. Repeat visitors = browsers with multiple sessions within that range. Active = browsers opening a page in the last five minutes, not heartbeat-based concurrent users. Daily figures count page views. Referring domains are carried through each browser session; missing referrals are direct/unknown. Country/location is not collected. Metrics refresh every minute while the dashboard is visible.

Tests cover persisted idempotent collection, excluded/private paths, dropped identifying fields, IST boundaries, visitors/sessions/conversions, origin restrictions, DNT and unauthenticated report access.

## Public tools statistics

`/tools/stats` displays aggregate AGI-wide metrics, linked from the Tools directory's traffic badge. `/api/intelligence/website-analytics/public-summary?days=1|7|30|90` is rate limited and cached for one minute; it exposes only an explicit aggregate projection. Arbitrary page paths and referring domains never pass through: routes become broad page groups, sources become search/social/referral/direct, and device/browser/OS values are enumerated. The original admin summary remains protected.

The visitor trend uses distinct browser IDs per IST hour for Today and per day for longer periods, including the incomplete current interval. Bucket visitors must not be summed into unique period visitors. Recent activity is page openings in five minutes, not concurrent presence. Browser/OS is parsed locally into coarse enums; the user-agent string is not transmitted. Older events are Unknown. No geo lookup, heartbeat, duration, bounce or campaign tracking is added. Public page/channel breakdowns reflect the top 30 entries of the underlying summary; omission is disclosed.
