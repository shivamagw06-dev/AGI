# AGI Finance Tools — prelaunch

Public route: `/finance-tools`. Admin review: `/admin/finance-tools`.

Finance-focused sponsored directory inspired by a pay-to-rank leaderboard. Search, categories, all-time/today controls and a deliberately labelled fictional example board are available. No invented companies, spend or clicks appear as real data. Public board is intentionally empty and checkout is unconditionally disabled in this release. No bid/payment endpoint exists.

Verified account holders submit a company name, public HTTPS URL, description, category and non-binding budget. The server derives identity/email from Supabase `/auth/v1/user`, never request fields. No remote URL scraping occurs. Application records are stored in a separate private `finance_tools.sqlite3` on the existing engine persistent disk, outside warehouse exports. Same-owner same-URL submissions deduplicate; max 10 applications/account. Personal applications filter by server-derived identity. Admin listing/review use the existing server-side administrator guard. Review status cannot create a paid rank. No outgoing email is sent automatically.

Payment activation is deferred per user instruction pending Razorpay approval. Before activation: settle sponsorship prices, tax/refund/placement terms separately from the consumer AGI subscription; implement signed, idempotent gateway webhooks and an immutable payment ledger; calculate all-time and IST daily rankings from settled eligible payments with deterministic ties; handle reversals and disputes; verify website representation before publishing. Never rank by the current indicative budget. Add real outbound links and measurement only when real listings can publish. Current fictional examples have no outbound links.

Existing membership pricing draft remains local and is not part of this release. Provider keys are neither required nor accepted by this prelaunch.

Validation: Python persistence/deduplication/ownership/validation tests, Node route authorization/identity-spoofing/payment-disabled tests, Vite production build and browser preview. Back up the private database with the persistent disk.

## AGI-owned tools

The directory now includes four permanent, clearly labelled Built by AGI listings, independent of the paid leaderboard and filtered by category/search: Model Studio (`/financial-modeling`), Holdings Explorer (`/institutions`), Valuation (`/tools/valuation`), and Peer Comparison (`/tools/peer-comparison`). Existing Model Studio account protection is unchanged.

New calculators are free browser-only tools. Valuation uses five years of constant-growth FCFF, year-end DCF, terminal perpetuity, an equity bridge, EV/EBITDA comparison and WACC/g sensitivity. Peer comparison accepts 2–6 manually entered companies; no live data is implied. Both support INR crore or USD million with matching share-count units, explicit missing/invalid states and CSV export. Currency selection only labels inputs, never converts them. Inputs are not persisted or uploaded. Ratios are descriptive and not stock rankings. Tests cover DCF reconciliation, invalid assumptions, loss/missing denominators and CSV escaping.

The directory uses a warm product-list layout and links to `/tools/stats`. The badge is AGI-wide recorded traffic, not a directory-only audience count or concurrent-user claim. AGI-owned products remain labelled separately from sponsorship, with no invented payments/ranks. Public statistics exclude raw visitor-level data and private path/domain details.
