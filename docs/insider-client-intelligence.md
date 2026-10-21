# Insider client intelligence

The homepage-linked `/insider-activity` page now includes evidence-led company cards and a shareable company detail view (`?company=<normalized company name>`). This layer reads the warehouse response independently of the historical-tape filters and never manufactures missing issuer context or source documents.

Signals use the last 30 calendar days ending on the current India date. They identify at least three named market buyers, purchases disclosed on at least three dates, promoter market sales, pledge invocation and individual market/block disclosures reporting at least 1% of company equity traded. These are explicit screens, not validated predictive scores. Names are normalized and duplicates removed; buyers are never claimed to be independent. Unknown, conflicting and non-market transactions do not count as buying conviction. Company detail compares available 30-day windows, separates transaction kinds, displays reported roles/ownership movement/trade period and links to original disclosures only where an HTTPS source URL exists.

The upstream feed is capped at 5,000 records and is not established as complete. No benchmark return, valuation, abnormal-activity claim, independent buyer determination, or historical hit-rate claim is produced. Missing documents are labeled. Old history does not become a current signal merely because it was the last imported activity.

Watchlists are local to the browser (localStorage), with a baseline of observed filings when saved. New or changed filing signatures appear as updates after refresh/revisit and five-minute checks while visible. Marking reviewed resets the baseline. This is not cloud sync, email or background notification delivery. Local storage failures are disclosed. Original financial data is not sent to an alert service.

Historical tape now supports loading every date in the returned feed. Requests are cancelled on filter changes to prevent older responses overwriting newer selections.

Validation: signal-boundary, duplicate, classification, watchlist-change, missing-value and safe-link tests in `src/lib/insiderIntelligence.test.js`, existing chart tests and a production frontend build. Browser visual QA is unavailable in this session.
