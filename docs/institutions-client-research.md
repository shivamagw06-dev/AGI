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
