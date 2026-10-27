# Institutions: source coverage, research and outcome tracking

The directory is available from 275 bundled source profiles even when the engine or its summary API times out. Public directory summaries are optional enrichment, never the source of current holdings counts. Each market/category has a separate cache, validated before use. Source rows are preserved in their files; current dated rows and historical/unknown rows have separate counts and an archive toggle. Never replace an unknown stake, trade or valuation with zero.

## Ownership research

`node scripts/institution_intelligence/build.mjs` builds summaries and same-quarter comparisons from the source files. It runs before production builds. Percentage precision defines a rounding interval: differences inside the combined interval are not definite increases/reductions. Missing prior quarters and newly disclosed threshold positions are not purchases. Group aggregates, corporate identities and unresolved personal identities do not count as independent fund votes. Counts are covered source profiles, not a market-wide institutional-flow metric. Source tables are not independently verified primary filings unless explicitly labelled in the research brief.

The reviewed primary-source briefs in `public/data/institution-briefs.json` separate facts, interpretation, conflicting evidence and watch points. Material edits require a NEW observation ID; previous observations and tracking dates cannot be overwritten. Further primary-filing verification remains a research-review step. This release does not certify all 275 imported profiles as primary-verified.

## Pricing

Exact security mappings are required. An explicit alias allowlist adds reviewed source-display names against the NSE master; there is no general fuzzy acceptance. Unknown / ambiguous names remain unresolved. Corporate-action and quote currency/identity guards remain. Valuations must match the holdings fingerprint. Partial totals show priced / total source rows and are not portfolio wealth or manager performance. Historical rows remain excluded.

The daily price workflow now runs at 04:15 IST (22:45 UTC), after US regular close in DST and winter. Original-disclosure checks retain their independent schedule. Manual valuations can include intraday prices and display actual quote times.

## Public outcome ledger

`Institutional Research Evidence and Registration` verifies the publicly served briefs match the checkout before registering first-public-observation times in the separate `institution-research-data` Git branch. It never backdates to ownership quarter, source retrieval or the date an analyst might have had the idea. Registration is retried manually if Hostinger has not yet served the artifact. The nightly valuation workflow reuses collected Yahoo adjusted-close histories (full history for the four researched stocks and two benchmarks) and updates the same ledger.

The baseline is the first completed **common** local trading session strictly after public registration. A same-day bar or an in-progress session cannot be the baseline. Matching stock/benchmark dates, currency and symbol identity are mandatory. Existing series and original registration dates survive missing prices or failed provider requests. Charts show adjusted-close stock returns and benchmark returns since that baseline; they are not executable fills, recommendations, short profits or investor-manager returns. No results exist before a baseline and sufficient closing observations. Provider histories can revise for corporate actions; series are research calculations, not an execution ledger.

Following a stock stores the selected comparisons in that browser only. A changed-comparison badge appears when that browser later receives a changed comparison for a followed stock. No external alerts, account access or paid services are created.

## Validation

- Node: rounding, unknown prior ownership, matching source periods, US date formats, market/category cache separation.
- Python: no backdating or intraday baseline, preserved ledger history on failures, immutable version IDs, symbol/currency identity and existing valuation/corporate-action guards.
- Browser: India/USA switching, saved-data failure state, company search/follow, profiles and archive toggles.

Option Lab remains paused. No trading flags, positions or broker-order paths are changed.

## Hedge Funds surface audit — 26 October 2026

The separate `/institutional-holdings` directory now includes the existing two primary-checked US observations and their shared chronological outcome feed. These remain separate from generated research-service approvals; no unreviewed note was approved. Tracking was not restarted or backdated.

The directory count comes from the returned manager rows. Consensus eligibility remains the existing service rule: latest report within 200 days of the newest report in that service. The page explicitly warns that this can mix quarters. The research library's broader manager count is labelled separately, not silently forced to match. No ranking or consensus rule changed.

Filing signals use each selected manager's structured latest filing and sort on `filed_at`, not alert ingestion. SEC publication dates use US Eastern; date-only inputs retain their calendar day. The old limited imported-alert sample is retained separately with an explicit AGI import-date label. This is not a comprehensive filing-event archive.

SEC submissions were checked directly on 26 October: Pershing CIK1336528 had a June2026 13F-NT accepted14August; Vanguard CIK102909 had a June2026 13F-NT accepted13August; Scion CIK1649339's latest listed 13F-HR covered September2025, filed3November2025. Notices must not be imported as holdings, and alternative-filer holdings must not be guessed. Directory and manager pages now explain historical/notice/failed statuses and link to the legal filer's SEC record. No positions or historical filings were replaced.

Overview methodology tiles are formula definitions, not empty numeric scores. Manager-specific scores remain on their manager pages. Research selected-tab and positive/negative text contrast were corrected on the light theme.

Validation: eight focused tests cover population boundaries, missing values, SEC timezone boundaries, status semantics, filing ordering/deduplication and ownership comparison safeguards. Production build passed. Browser preview used recorded public overview/research responses to avoid localhost CORS; final verification uses production directly. No database, Render setting, broker or Option Lab change was required.

## Full selected-manager source review — 26 October 2026

The Hedge Funds page now has a separate source-checked snapshot covering all 50 selected legal filers. The collector reads SEC submissions and original latest/prior information tables with TLS verification, a shared request limiter below five requests/second, bounded retries and a daily local read cache. No admin refresh, database write, broker setting or recurring paid service was used. Runtime collection uses BeautifulSoup4 and optionally certifi for the system certificate bundle; the offline tests require only Python's standard library.

Results: 47 June2026 original-filer tables, two newer 13F-NT notices (Pershing and Vanguard), and Scion's historical September2025 table. A matching latest-quarter label does not establish current live ownership. The selected universe includes corporations, banks and asset managers; it is not 50 independent hedge-fund votes.

Seventeen identity-reviewed Dataroma profiles were checked. 620 quantities matched via existing exact CUSIP-to-symbol identities: 615 agree directly; five Maverick quantities are consistent with later splits (MNST2:1, APH2:1, CRWD4:1, GUTS1:12 and CRIS1:20), allowing less than one share for reverse-split presentation rounding. Primary issuer/exchange sources and each original/secondary quantity are shown. This does not claim to validate the secondary site's adjustment methodology or every row: unmapped rows remain explicitly unverified. WhaleWisdom's rendered Appaloosa profile was also checked; its total includes two put rows measured on underlying shares, while Dataroma excludes them.

Pershing's June notice names Pershing Square Inc. (CIK2026053). That parent's June table was separately read and all14 mapped quantities agree with Dataroma. It is shown as a separate reporting scope, not silently substituted for or merged into the old legal filer's history. Vanguard's ten notice-named reporting entities are linked; their portfolios have not been consolidated or independently audited in this release.

Norges Bank's current June table is readable, but the prior March information-table file contains a single NA/zero placeholder while its cover declares1,507 entries. Its quarter comparison is withheld. No holdings are invented, no placeholder becomes a stock, and its valid current table is not erased by the prior-source failure.

The full audit stays in the local cache; public JSON retains metadata, source links, original unit/type counts and up to five largest displayed increases/new disclosures plus five reductions/absences per filer. CUSIP, quantity unit and option side identify distinct records; repeated discretion rows are combined, while changed class wording is flagged and excluded from displayed change leaders. Quantity comparisons are unadjusted filing quantities, not trading flows; corporate actions and manager motives are not inferred.

Three reviewed summaries cover Tiger/Appaloosa disagreement, Akre's reductions and Appaloosa's selective China exposure/options distinction. They are dated multi-stock research notes, not additional price-tracked observations. The existing four observation IDs, first-public dates and outcome histories are unchanged. Underlying backend holdings/consensus are not rewritten by this read-only audit. The dated source snapshot is displayed separately from service-derived research.

Validation: six offline parser/reconciliation/snapshot tests plus eight existing disclosure/ownership tests; production build; browser checks for all50 records, search, Pershing's alternate filer and all five split reconciliations. The evidence workflow now runs the new tests before release.

### Client additions and reductions — 27 October 2026

The institutions directory (both country tabs) and the US institutional-holdings overview now include a curated client section from `public/data/client-holdings-intelligence.json`: 38 manager/category comparisons across seven US securities and two Indian companies. US quantities reconcile to the full 26 October SEC audit cache; Indian ownership percentages reconcile to the existing primary-checked briefs. These are selected examples, not a comprehensive ranking or market-wide count. Reporting dates, US latest filing dates, both source documents and separately labelled interpretation are retained per row. Country-specific units distinguish share-quantity percentage changes from ownership percentage-point changes. Search and direction filtering do not change the evidence. This dated editorial snapshot is not automatically refreshed or separately registered for price-performance tracking.

Validation: all 38 comparisons checked for chronology, direction and arithmetic; US values checked against the full audit, identity-review rows excluded. Existing eight institution/disclosure tests and production build passed. Browser preview checked search, source links and rendered table layout.
