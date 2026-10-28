# Screener intelligence

Every imported and legacy stock screener displays four research cards above its table: two screen-specific observations, cross-screen context and data freshness. A separate strip compares the prior saved publication. All calculations are deterministic and use saved inputs; no LLM calls, broker requests, background workers or new paid services are introduced.

## Automatic updates

- The latest table and its summary check every five minutes while visible and when the tab becomes visible. The summary is pinned to the displayed snapshot ID, so its figures cannot describe a different list.
- Publishing changes saved inputs; the next page check recalculates the evidence. Trendlyne source collection remains manual. Polling is not a new source-data import.
- The backend shares a 60-second cache for cross-screen inputs, invalidated by library publications. It reads current custom snapshots in one batch plus the five existing screen tables. No database schema or grant changes are required.
- Selected historical publications stay selected. Cross-screen context and the All-Weather factor intersection are withheld in saved views to avoid later-publication look-ahead. Entry/exit changes compare only the preceding saved publication.

## Interpretation

Medians exclude missing and invalid inputs, including non-positive ratio denominators. Each card shows coverage. Growth is FY2/FY1 minus one; earnings yield is 100/forward P/E; ownership changes are percentage points; volume multiple is daily volume / weekly average; sector-relative change is stock minus sector change in percentage points. Low P/E discount is one minus trailing P/E / historical P/E, not price-target upside. Six-period FCF consistency requires all six values to be strictly positive.

Same-date overlaps separate code/ISIN matches from provisional exact-name matches. Conflicting supplied identifiers cannot be rescued by names; changed identifier coverage withholds apparent entry/exit churn. Ownership intersections additionally require the latest completed quarter, excluding older, missing and later/non-quarter-end observations. The parent All-Weather union is excluded from individual factor cross-screen comparisons. Related screens do not represent independent confirmations.

All-Weather displays provisional names common to all four saved factor screens and to at least three, only when all four tables share the current data date. These are not portfolio weights, calibrated rankings or probabilities.

## Limits and access

The report explicitly distinguishes calculation time, table date and underlying reporting periods. Table age over seven calendar days receives an older-snapshot badge; this is a calendar-age disclosure, not a claim that younger prices are live. Missing statement/event dates are disclosed. The auditor watchlist is never labelled a new resignation event. No forward performance, trade fills, price targets or predicted success are invented.

`GET /api/screener-library/:slug/intelligence` uses the same verified member/admin authorization as imported results. Snapshot IDs are validated, responses are private/no-store, and anonymous or inactive accounts cannot trigger research reads. Existing legacy result endpoints are unchanged.

Tests cover arithmetic, missing values, invalid dates, quarter alignment, identity changes, look-ahead prevention, access controls and the absence of raw rows in intelligence responses. All 21 saved source datasets were also checked locally before release.
