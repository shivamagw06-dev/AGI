# AGI Hedge Fund Intelligence Terminal

`/hedge-fund` is a daily institutional research workspace, not a course, a
screener or a recommendation engine. It runs professional strategy screens
across the covered Indian equity universe and answers one question: where
should a research team spend its time today?

## Architecture

```
institutional warehouse (nightly refresh ~18:45 IST)
  company_master · historical_valuation · valuation_ratios (Upstox)
  historical_ratios · consensus · daily_market_history · hedge_fund_factors
        |
market_intelligence_engine.universe   joined live multiples + consensus
        |
hedge_fund_lab/scanner.py     value, quality, momentum, conviction, stress, pairs
hedge_fund_lab/terminal.py    growth, dividend, confidence, overlap, queue,
                              regime extension, market dashboard, snapshots
        |
warehouse refresh stage "hedge_fund_lab"   writes daily scanner snapshot
        |
/v1/hedge-fund-lab/terminal          the whole page in one call
/v1/hedge-fund-lab/scan/{strategy}   one scanner, full rows
/v1/hedge-fund-lab/opportunity/{tk}  why one company qualified
```

Scanners read the warehouse only — no vendor calls at page load. The Yahoo /
CapIQ file stores remain a soft fallback when the warehouse universe is empty.
Every derived number is computed server-side. The browser renders, it never
calculates.

## What the page shows

1. **Market regime strip** — stance, breadth, advance/decline ratio, median
   one-year return, return dispersion, median P/E, valuation stance,
   consensus upside, institutional sentiment, most and least attractive
   sector, universe size.
2. **Hero counters** — universe scanned, strategies running, live
   opportunities, companies flagged, multi-strategy names, plus highlight
   tiles for the strongest result in each category.
3. **Live strategy scanners** — eight scanners (value, quality, growth,
   momentum, consensus conviction, dividend, stress, market-neutral pairs)
   with opportunity count, average confidence, regime suitability, alpha
   source, risk level and today's entries.
4. **Opportunity tables** — every row carries the company, sector, industry,
   confidence, consensus and a written reason. Expanding a row calls the
   explain endpoint: strategies matched, the calculation chain, risks,
   catalysts, evidence by source and the scanner timeline.
5. **Strategy overlap** — companies reached by more than one independent
   scanner, ranked by agreement and confidence.
6. **Research priority queue** — the ranked morning list with a reason and
   an estimated research time, weighted toward names with institutional size
   or broker coverage.
7. **Daily intelligence** — what entered and left each scanner against the
   previous recorded scan.
8. **Market dashboard** — sector valuation table, largest discounts and
   premiums to industry, highest return on equity, highest consensus upside,
   and factor readings across the universe.
9. **Strategy library** — the educational layer, deliberately below the live
   surface.
10. **Calculators** — exposure, expectancy and pair-trade maths, server-side.

## Confidence

Confidence is a bounded 25–95 score derived from the strategy's own strength
measure (discount to industry, quality score, implied growth, relative
strength, broker agreement, yield, stress flags, spread width). It expresses
how strongly the data satisfies the screen. It is not a probability of profit
and not a recommendation.

## Snapshots

The warehouse nightly refresh runs a soft `hedge_fund_lab` stage after
`recalculate` / `publish`, which records the day's scanner membership under
the hedge fund lab store (`HEDGE_FUND_LAB_ROOT`, else
`KIP_DATA_DIR/hedge_fund_lab`), keeping 60 days. Opening the terminal page
also refreshes today's snapshot. Day-on-day entries and exits, and the
per-company timeline, are computed from those snapshots.

## Data hygiene

Vendor pulls carry outliers. Metrics outside plausible bands are treated as
missing, a trailing-to-forward gap implying more than 100% earnings growth is
rejected as a data artefact, and dividend yields above 12% are excluded while
yields above 8% carry a special-dividend warning.

## Not built yet

Stated plainly so the page is not mistaken for more than it is:

- **India VIX** is not wired in; return dispersion stands in for it.
- **Intraday microstructure** — momentum uses warehouse one-year returns
  (from `daily_market_history`) and CapIQ three-year returns when present,
  not moving averages, 52-week position or volume.
- **Historical hit rates and historical opportunity counts** per strategy
  require snapshot history; the fields appear once enough days accumulate.
- **Cointegration and spread history** for pairs need a price time series.
  Pairs are currently a cross-sectional valuation gap within an industry.
- **Portfolio builder, long/short book construction and market-neutral book
  generation** beyond the existing exposure and expectancy calculators.
- **Merger arbitrage, event-driven, global macro, commodity and volatility
  scanners** need deal, event and derivatives feeds that are not connected.
- **Corporate actions and results feeds** are not yet part of the timeline.

## Policy

The terminal never issues a buy, sell, target price or personalised
recommendation. Every opportunity states why it exists, which data supports
it, which scanner found it and what could invalidate it. Market data,
consensus data and AGI interpretation are labelled separately throughout.
