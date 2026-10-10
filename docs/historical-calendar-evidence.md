# Historical event calendar evidence

Work in progress; not connected to live review records or backtest promotion.

`options_lab/historical_calendar.py` compiles explicit, sourced retrospective
session coverage into the existing calendar shape. A known event is not permission
to clear an entire session. Missing category coverage remains blocked. The proposed
research blackout is 30 minutes before to 60 minutes after an announcement; this
is a separately declared experiment assumption, not an inferred historical fact
or an alteration of live rules.

The JSON inventory contains four official time-stamped Indian releases and eight
Federal Reserve scheduled policy statements in the requested year.
All were scheduled at 16:00 IST, after the normal trading session. They cannot
legitimately create an intraday post-event iron-fly opportunity on those dates.
The Federal Reserve timestamps retain EDT/EST offsets and are converted to IST,
including next-day rollover. Minutes and speeches are not covered. RBI
announcement times, Budget and complete session-level coverage remain unfinished. No session clearance has been fabricated.

Verification: calendar validation tests check withholding incomplete days, aware
timestamps, source references and blackout generation using synthetic fixtures.
These are software tests, not performance backtests. The seven historical research
strategies still require completed calendar evidence before a meaningful rerun.

Latest local verification: 15 tests and 9 subtests passed, including US daylight
saving offsets and midnight clipping. No new strategy P&L was generated.

## RBI addition — 2026-10-02

Added scheduled 10:00 IST monetary policy statement starts for 6 February and
8 April 2026 from RBI's own LinkedIn announcements (URLs in the JSON inventory).
These are scheduled broadcast starts, not verified first dissemination timestamps.
Four further dates are recorded separately with timing unresolved: 1 October and
5 December 2025, 5 June and 5 August 2026. Sources establish meeting dates or
statement dates; they do not justify assigning an exact announcement time.
The compiler blocks a date containing an unresolved event even if coverage is
otherwise supplied. No live reviews were written. Inventory now holds 14 timed
events and 4 pending dates. Local calendar/pipeline verification: 17 tests and
9 subtests passed. Not deployed and no new performance results generated.

## Oil, geopolitical and macro-news context

`options_lab/macro_context.py` is a separate research helper, not connected to
live strategy decisions. `available_news` admits only recorded, unrevised items
with source provenance and aware publication/receipt times; date-only historical
news stays excluded. It does not assign bullish/bearish direction or manufacture
scheduled blackouts. The inventory contains an IEA oil release and conflict-onset
context; the later IEA report must not be used as a February trading signal.

`oil_move` measures a percentage change between comparable, sourced same-contract
quotes with known receipt times. It rejects stale/nonfinite prices, future
receipts and futures-roll mismatches. No oil quote series is connected yet;
Brent/WTI history, instrument mapping, timestamps and provider rights must be
verified before this helper can generate real observations. No fixed shock
threshold or automatic call/put rule has been added.

20 tests plus 9 subtests pass across macro context, calendar and validation
pipeline. These changes are local; no deployment or new strategy P&L.
