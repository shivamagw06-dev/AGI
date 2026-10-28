# Institutions publishing

Public page: `/institutions?country=IN` or `US`. The old `/rich-kids` URL redirects and preserves its country selection. Admin page: `/admin/institutions-paste` (also in admin navigation).

Choose a market, copy the full source table including headers, optionally enter its valuation date, Check table, then Publish. Publishing replaces the complete selected market snapshot. It never modifies the other market. The initial 11 India entries remain visible until an India snapshot is published. USA remains empty until its first publication.

Supported headers: Superstar, Portfolio Value* (change), #Of Stocks, Sector Preference, Quarterly Net Worth (optional), Top Holdings, Recently bought, Recently sold. Rich HTML table clipboard, quoted multiline TSV, CSV and Markdown tables are supported. Rich clipboard retains HTTPS links, line breaks and cell boundaries, omitting SVG/image chart data. Plain copied text cannot preserve hyperlinks or sparkline values; missing fields are not invented.

India values must specify Cr and remain INR crore. USA values must specify M and remain USD million. Arrow/signed change percentages, comma grouping, multiline holdings and sectors are supported. Names identify investors within a snapshot: exact duplicates collapse, conflicting duplicates reject the entire paste. Invalid rows, units, dates and unsafe links block publication. Quarterly text/figures are displayed only if supplied; no historical charts are reconstructed from pictures.

Preview and publish require the existing server-verified administrator guard. Engine read/write routes require the engine token, which stays server-side. Snapshots persist as one JSON row per country through the warehouse gateway, preserving its validation/audit workflow and atomic row replacement. Public reads do not cache snapshots. Open pages refresh every minute while visible, and include a manual refresh button.

Validation includes India/USA screenshot-shaped fixtures, rich HTML clipboard-to-parser verification, real isolated storage publication and replacement, country isolation, invalid-paste preservation, missing change/quarterly values, safe links, duplicates, anonymous and non-admin access rejection, regression tests and production frontend build. No test data is published to the production database.
