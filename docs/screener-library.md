# Screener library and unified importer

Member entry: `/agi/screeners`. Admin entry: `/admin/screener-import`.

## Publishing

1. Select an existing screen, or create a definition with a unique URL name and category. Definitions are visible in the library; stock results are absent until an import is published.
2. Choose the source data date, optionally record an HTTPS source URL, and paste a complete CSV/TSV table with headers. Excel/Sheets cell copies work. A second part can be supplied with its header; new screens accept reordered matching headers across the two parts.
3. Check the table. Up to 5,000 stocks and 120 columns are supported for new screens. Repeated headers are collapsed only when their values agree. Missing/duplicate stock identifiers, invalid ISINs and malformed row widths block import. ISIN is preferred automatically; the administrator can choose a different complete unique column.
4. Review rows, date and source. Confirm and publish. The server reparses the original table; it does not trust a browser-supplied row count or preview.
5. Members can search/sort stock tables, browse saved publications and see entries/exits compared with the preceding publication. Comparisons are withheld if the identity column changed. Entries/exits describe list membership, not trades or performance.

Drafts remain in memory per selected screen while this admin page remains open; reloading closes those drafts. CSV/TSV file import is supported; binary Excel files should be copied as cells or saved as CSV first.

The 16 editable starter definitions have no invented results. An administrator may create additional definitions. The five pre-existing screens remain linked and use their original validated import services and saved history. Low P/E moves to `/agi/screeners/low-pe`; `/agi/screeners` is now the library. Low P/E exceptions still require explicit acknowledgement and are never silently published.

## Data meaning

New screen rule notes are descriptive text, not executable formulas. The generic importer does not calculate DVM scores, analyst estimates, valuations or technical signals, or certify that a pasted table meets those rules. Existing specialised screens retain their existing financial checks. Data is administrator-published and dated, with no automatic Trendlyne scraping or live refresh. Source permissions remain the publisher's responsibility.

A publication retains its original definition, date, source and stock values. The latest publication cannot move backwards to an earlier data date. Same-day corrections produce another saved snapshot. Repeating the same table/date/source is idempotent. Published snapshots are append-only for the backend role; member/browser roles cannot access their database tables directly.

## Access and operations

The new result and history APIs verify the Supabase identity and an active AGI Plus membership server-side; admins bypass membership. Create, edit, preview and publish require a verified admin identity. Public catalogue metadata contains definitions and availability, not result rows. No service credentials are included in the client.

This protects the new library datasets. It does not retrofit the older five public result APIs or unrelated pre-existing public datasets. The existing membership page gate remains in place around tool pages.

There are no new Render services, paid APIs or scheduled collectors. The library uses the existing Node API and Supabase project. Metadata uses a 30-second cache for clients; the authenticated admin catalogue reads fresh data. Snapshot history selectors show the 100 most recent publications; older stored snapshots remain addressable by ID. Entry/exit lists show at most 100 names per side; full saved tables remain available for inspection.

## Validation

`node --test src/lib/screenerTable.test.js server/routes/screenerLibrary.test.js server/services/manualLowPeScreener.test.js src/lib/pastedTable.test.js`

Database rollback tests cover retained histories and original definitions, duplicate publication idempotency, latest-catalogue pointers, backdated publication rejection, browser-role denial and service-role immutability. They create no durable sample stock rows. Before release, verify the actual legacy data in the library, the empty-state for an unpopulated definition and a live admin preview. Do not publish made-up prices as a production test.
