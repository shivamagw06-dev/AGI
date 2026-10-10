# AGI Alpha Validation and Investment Operating System

## Purpose

This system separates trustworthy data, interesting research and capital-ready
strategies. A scanner, factor or live observation is not called alpha until it
passes point-in-time, statistical, economic, execution, paper and live gates.

## Immutable objects

Every strategy version has a content hash. Formula changes create a new
strategy version. Every research run binds the strategy definition, code
commit, dataset, historical universe, feature definitions, corporate actions,
cost schedule and parameters into one reproducible manifest.

## Sequential status

`DEFINED -> DATA_VALIDATED -> RESEARCH_VALIDATED -> ECONOMICALLY_VALIDATED -> PAPER_VALIDATED -> LIVE_VALIDATED -> PRODUCTION`

Strategies may move backward to `SUSPENDED` or `INVALIDATED`. Capital is
blocked unless both the declared status and all recorded gates are production
eligible.

## Legacy-data policy

The Capital IQ master workbook is authoritative for reported annual values but
most historical rows are `PIT_LIMITED`: they do not prove when AGI could have
known each value. Historical valuation rows reconstructed in 2026 are also not
historical point-in-time observations.

Those rows remain available for descriptive research. They are excluded from
alpha validation. The prospective collector records their first defensible
`available_from` timestamp as the time AGI possessed the warehouse revision;
it never backdates that timestamp to the fiscal period or original filing.

## Daily prospective validation

At 18:45 IST each weekday, after valuation collection, the workflow:

1. Captures declared Capital IQ facts with honest availability timestamps.
2. Captures the latest observed valuation state.
3. Captures corporate actions without backdating AGI knowledge.
4. Maintains an effective-dated investable universe from the first snapshot.
5. Writes a hashed readiness report for all fourteen governed strategies.

The workflow never promotes a strategy, allocates capital or places an order.

## Strategy roles

- Relative Value, Quality, Growth and Momentum are factor research.
- Value plus Quality is a pre-registered factor combination.
- Consensus is revision and expectation research, not target-price upside.
- Stress is a risk detector.
- Volume Anomaly is an event detector.
- Pairs is a candidate generator until cointegration, borrow and execution pass.
- Derivatives Positioning is a descriptive feature.
- Opening Range and Mean Reversion are execution- and event-conditioned research.
- Multi-factor is a future portfolio model, not an optimized production score.

## Current honest status

The implementation is ready to collect valid forward evidence. Historical
fundamental strategy validation remains blocked until enough point-in-time and
historical-universe coverage accumulates or authoritative vintage data is
imported. That is a data limitation, not a reason to manufacture a backtest.
