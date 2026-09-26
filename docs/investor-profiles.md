# Investor profile pages

Every name in the published 63-investor India and 71-investor USA directories links to `/institutions/:country/:investorId`. Country and a normalized-name hash identify profiles; identical names in different markets remain separate. Existing administrator-published directory snapshots remain authoritative for the summary cards.

The dated detail collection contains 134 profiles, 122 with holdings, and 24,415 disclosed security rows. See `investor-profile-coverage.csv` for each profile's source, period, row count and coverage. Remaining profiles explicitly show that detailed holdings are unavailable, alongside their published summary. Partial source tables are labeled partial; no missing holdings are synthesized. Some source pages are cached historical snapshots and some cap their tables at 200 rows.

Sources are public Trendlyne portfolio tables, Dataroma holdings tables the existing public AGI SEC filing archive, and supplemental ValueSider/Terminal001 snapshots. Each detail file retains its source URL, source period, retrieval date, source-reported count and coverage state. Only factual table fields are shipped, not source commentary. SEC filing entities are named separately from the investor, and their weights are labeled portfolio weights rather than company ownership. Share classes, options and share/principal units remain separate. SEC filings marked `needs_review` are excluded from this collection.

Detail files are loaded on demand, one investor at a time. Tables offer company/holder search, movement filtering where supplied, 50-row pagination, Indian quarterly ownership history and a CSV download with provenance and security identifiers. CSV fields are quoted and formula-leading text is escaped. Missing values remain unknown; a below-threshold disclosure is not classified as a verified exit.

This release is a dated collection retrieved on 2026-09-26, not an automatic ingestion service. Pasting a new summary table does not update the separate detailed snapshots; the UI states that distinction. No admin authentication, publication endpoints, database writes or permissions were changed.

## Rebuilding the collection

`scripts/build-investor-profiles.py` converts locally collected web retrievals (`/private/tmp/agi-portfolio-web-sources.json` and optional `/private/tmp/agi-portfolio-dataroma-sources.json`) and SEC JSON snapshots under `/private/tmp/agi-investor-sec` into profile JSON. These local inputs are not committed. Source tables are joined by their numbered retrieval lines and aggregate rows are kept separate from repeated holder details. `scripts/fetch_investor_sec_snapshots.py` only reads existing public AGI filing endpoints; it does not authenticate or publish.

Validate an updated collection with `node --test src/lib/investorProfiles.test.js` and `npm run build`. The initial release additionally exercised rendered India history, US security rows and pagination, back navigation, and unavailable-source summary pages through React with a local DOM.

Supplemental snapshots in `src/data/investorProfiles/supplemental.json` cover Robert Karr (10 positions, 2026 Q1) and a partial Ron Baron excerpt (40 weights, 2026 Q2). The final collection has 111 retrieved disclosure snapshots, 11 partial tables, and 12 unavailable detailed sources.

## Daily price-based valuations

The `Investor Portfolio Nightly Valuation` workflow is scheduled for 20:30 UTC (02:00 IST the following day), including weekends. GitHub can delay scheduled starts. It can also be run manually. This refreshes prices, not the underlying disclosure quantities or pasted summary. At 02:00 IST the US regular session is still open during US standard time; quotes are not always closing prices.

The public JSON is atomically committed to `investor-valuations/latest.json` on the dedicated `investor-valuation-data` branch and read through raw.githubusercontent.com. The branch is machine-owned and never merged into main. Only this public data file changes; source and deployment branches remain untouched. The job uses its repository-scoped GitHub token; no FTP credentials are needed. The raw-content CDN can take several minutes to reflect a new commit. Pricing failures fail the workflow and preserve the previously published file. The UI shows the last successful refresh and flags it overdue after 36 hours. Ordinary frontend builds do not own this file.

Yahoo chart regular-session prices are used for exact NSE-master name mappings or existing AGI CUSIP/ticker mappings. Explicit ticker prefixes supplied in fund-disclosure rows are also accepted. No fuzzy name lookup is used. Options, principal units, preferred securities, warrants, absent quantities, unknown/old disclosure dates, stale prices, currency mismatches and securities with a split since the disclosure date are excluded. Values are estimates based on disclosed quantities, not actual positions or personal wealth. Partial subtotals are explicitly identified; filing values are preserved separately. Changes compare the same disclosed quantities at latest price versus previous daily close; they are not investor returns. Missing prices are never zero. US rows without a CUSIP mapping or explicit source ticker remain unpriced.

The frontend checks a shared SHA-256 fingerprint of disclosure inputs before attaching quotes to individual rows. Updating a holdings file invalidates old row valuations until the next refresh. Directory estimates display their own disclosure period, separate from an administrator's current summary.

`build_mappings.py` generates reviewable mappings from the local NSE equity master files and existing cached AGI SEC holdings. Refresh/review these mappings when companies rename, listings change or new disclosure rows arrive. Yahoo is an unofficial integration and may rate-limit access; no proxy or access-control bypass is implemented. Yahoo data availability does not establish commercial redistribution rights; confirm applicable provider/exchange permissions for public client-facing use.

Tests: `python3 -m unittest discover -s scripts/investor_valuation -p 'test_*.py'`, `node --test src/lib/investorValuations.test.js src/lib/investorProfiles.test.js`, and `npm run build`.
