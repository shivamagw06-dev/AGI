# Main 25 and reserve 25

Branch: feat/factor-main-reserve. Built on the existing October source implementation. This feature is not activated by deploying code alone and does not alter any stored allocation at startup.

## Selection

The supplied 11 October 2026 India report explicitly labels Figures 12/14/16/18/20 (pages 7/9/11/13/15) as sorted by factor score. The verified 250-record instrument mapping is stored in server/data/factorCandidates.json. Preserve displayed order within rounded-score ties. Main = first 25 at 4% target each; reserves = remaining 25 at 0% in the main account. This changes the published 50-stock construction; it is not a fresh ranking or an exact replication of the research long/short factor series. No new liquidity or sector cap is silently applied.

## Screens and API

Each of the five India factor detail pages adds a main table, expandable reserves, individual reserve chart selector, shared-start comparison and sector exposure. Existing continuous-ledger performance remains intact. Before a dated execution, the new selection is explicitly proposed and shows no invented return.

GET /api/portfolios/:id/factor-selection returns the ranked 50, dated closes, available fresh quotes, separate comparison lines, missing-data status and pending-date metadata. Shared live quote requests cover the 168 unique symbols once for all five portfolios, with single-flight caching for four minutes and existing provider budget controls. Live composite comparisons are withheld unless all 50 quotes and the common baseline are valid. Provider timestamps are retained. No live requests occur outside the NSE session.

POST /api/portfolios/:id/factor-selection/rebalance requires existing admin authorization. The server constructs the verified 25-stock target rather than trusting arbitrary client ranks. Existing CAS and future-session checks apply. A pending request is cancelled and replaced in one atomic ledger write, retaining the cancellation and new schedule in the audit. No broker order endpoint is involved.

## Daily evidence and accounting

At the effective close, the collector requests held/new instruments first, then all reserve candidates. Only held instruments are required to mark the main account. All 50 are needed for comparison points. Main25/reserve25/all50 use the same baseline date, equal initial weights and buy-and-hold price returns, before dividends and costs; the separate continuous portfolio ledger reflects its recorded rebalance costs. Missing comparison dates remain missing rather than changing weights or forward-filling.

Successful shared daily lookups are reused across portfolios within a collection cycle. The existing immutable ledger history retains its exact prior objects. Missing reserve prices may be recovered for seven days in an additive factorEvidence field; this never overwrites published NAVs, events or prices. Missing activation-close evidence withholds comparisons instead of moving the baseline to a later date. Longer gaps require review.

## Validation

24 focused tests cover all five 25/25 splits, 100% main weights, score order, missing and recovered evidence, identity matching, future/stale live quotes, reserve exclusion, historical NAV preservation, validated scheduling, atomic replacement, API administrator access and shared quote caching. Production Vite build passes. Local desktop 1440x900 and phone 390x844 previews use actual saved source/portfolio records and intentionally leave new returns blank. Phone document width is 390px with no page overflow; tables scroll within their container.

## Release / activation

1. Publish the backend and frontend together; no schema migration is required.
2. Verify the selection endpoint against real ledger rows and verify broker credentials through existing health controls.
3. In each portfolio detail page, open Admin > schedule this 25-stock allocation and choose a future exchange trading date. This replaces any pending 50-stock request atomically; it does not backdate execution. The local calendar rejects 20 October 2026.
4. Verify 25 holdings at 4% in the scheduled target. After complete execution-day held-stock closes arrive, verify the ledger rebalance event and preserved earlier NAVs. Reserve gaps must appear only in comparison status.
5. Verify all 50 quotes during a live market session and collect the activation-close baseline before describing tracking as live.

No production allocations, pending requests or historical returns were changed while building this branch.

## Separate September 15 current-holdings backtest

The five factor pages now expose a retrospective view from 15 September 2026 close: first 25 of the fixed October snapshot, 4% initial weight each, buy-and-hold thereafter. Because the selection postdates the start, the UI explicitly identifies selection look-ahead; it is not evidence of a strategy selected in September. Raw INR price returns exclude dividends, fees and taxes; corporate actions require review. Actual activation, pending requests, execution events and continuous published NAV remain untouched.

The existing ledger document stores separate `factorRetrospective` evidence, keyed by source snapshot and verified instrument identity, using existing CAS writes and server authorization. No new table or public write access. Off-market collection is bounded to five instruments per portfolio per scheduled pass, with shared instrument requests across the five portfolios and the existing market-data budget. Each historical range request returns daily bars from the start through the latest completed NSE session. Partial results persist; failures retry after an hour. Previously saved observations are retained. Current daily quotes do not substitute for historical prices.

The exact 15 September baseline requires all 25 prices; no late baseline shift or removal/reweighting of missing stocks. All-25 daily gaps appear explicitly, break the chart line and withhold the corresponding composite point. Stock charts can show their available bars independently. The page shows latest complete basket date and incomplete dates; collection does not claim full coverage until every expected session is present. After implementation release, verify real provider coverage for all five before reporting numerical results. September history collection is research data retrieval, not a backdated allocation or broker trade.

Historical basket collection has its own single-flight five-minute scheduler, independent of USA symbol downloads and continuous-account collection. Its bounded off-market requests still use the shared provider budget. A USA backlog cannot prevent it from starting. Concurrent account updates cause CAS deferral, never history loss.

## All India historical returns and reserves

September history now covers every stored India allocation: the five factor portfolios, Preferred, Conviction Long, Conviction Short and the existing private Growth + Momentum experiment. Each factor portfolio collects all 50 candidates, with its main 25 at 4%, reserves at 0% in the main basket, plus separate equal-weight Reserve-25 and All-50 comparisons. Other portfolios retain their actual current weights and cash. Conviction category comparisons use the original within-category weights and preserve overlapping stocks; aggregate weights remain those of the current stored combined allocation. Short research uses 100 plus the weighted opposite of constituent price changes, excluding borrowing, margin and dividends owed.

GET /api/portfolios/:id/retrospective returns stock baseline/last close, dated price history, price return and signed strategy return for every candidate, plus portfolio/category/comparison baskets. Existing ledger access controls protect private portfolios. GET /api/portfolios/india-retrospectives exposes only public portfolio summaries, without stock holdings or private allocations. The India library adds a clearly labelled retrospective return; detail pages have full stock tables and historical charts alongside the immutable actual allocation record. Main/reserve tables also show a separately labelled September return.

The collector now prioritizes missing baselines, handles ten instruments per India portfolio per pass, and reuses verified instrument-key-matched historical prices and daily closes across all India portfolios. It can fetch the completed current session's intraday daily candle when the range API omits today. A failed current-day lookup retains successful historical bars. Five-minute retries use the existing global provider budget. Missing baselines withhold composite returns without dropping stocks; individual returns can publish independently. Recorded prices, account NAVs, rebalances and private visibility are preserved. New current-allocation specifications get a deterministic membership/weight hash; raw price evidence can be reused by identity, while the view requires the matching specification.

Validation includes generic weights/cash, short sign, shared category stocks, all 50 candidates, missing-stock non-renormalization, baseline prioritization, current-session close recovery and public/private route separation. Public current allocations contain 222 unique instruments across the eight portfolios (including factor reserves); all current weights total 100%. No September performance is presented as an actual September stock selection.

### Verified NSE gap supplement

ZEEL's Upstox range history remained unavailable after repeated scheduled attempts, although its current daily prices were present. `server/data/indiaNseHistoricalSupplements.json` stores 25 verified NSE official daily closes from 15 September through 21 October 2026, with each source archive URL. Every row was matched on trading date, EQ series, ZEEL symbol and ISIN INE256A01028. The supplement fills missing research prices only; previously observed prices retain priority. It never rewrites actual portfolio NAV, execution events or dated positions. Symbol and instrument key must both match before use. The historical stock table explicitly labels the NSE backup, and its overall source note distinguishes provider daily prices from archive supplements. Future dates still use the regular collector.

Independent audit matched all 221 broker-provided September baselines against NSE's 15 September closing file; the verified supplement supplies the 222nd. Provider daily-candle closes may differ from NSE's official weighted closing price on a current session; this historical view discloses its price source and is not an independently adjusted total-return record.
