# USA daily tracking

All published USA allocations use reviewed Yahoo USD equity/ETF mappings. The default period begins at the adjusted close on 15 September 2026. This is a retrospective current-allocation buy-and-hold simulation, not an actual September launch or a historical rebalancing ledger. Changing holdings recomputes the comparison. Existing monthly horizons remain available.

Each portfolio and holding has a daily chart; tables show adjusted starting/end prices, returns and contribution in percentage points. Missing sessions, IPO history or incomplete allocations withhold the composite rather than rescale covered names. Tiny original weight rounding is handled by the existing calculation method.

`/api/portfolios/usa-history` serves a shared snapshot. The existing Node service checks hourly and refreshes after 17:00 America/New_York; DST is handled by Intl. It collects daily history for the reviewed universe (including SPY for common sessions) once per date, sequentially with 300ms spacing and 20s per-request timeouts. 401/403/429 or benchmark failures retain the last dated snapshot and surface an error. Missing individual series remain unavailable. Concurrent refreshes coalesce. No broker credentials or paid resources are used.

Cache is written atomically under DATA_DIR if set, otherwise the OS temporary directory. The committed snapshot is the restart fallback. This is a rebuildable adjusted-price cache, not a durable trade/accounting ledger. Yahoo can revise adjustments. UI explicitly shows the final price date and stale/error warnings.

Verified seed: 305/305 securities downloaded, through 2 October 2026, from Yahoo. USA portfolios contain 266 distinct funded securities. Exact-date and common-session validation checks all 26 allocations against this seed.
