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
