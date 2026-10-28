-- Index rebalance tracking: FTSE and MSCI reviews, and the passive flow
-- expected against each affected name.
--
-- The shape of these tables follows one distinction. A rebalance table has two
-- kinds of column, and conflating them is what makes a published one stale:
--
--   Fixed by the event. Ticker, the type of change, the effective date, and
--   the flow estimate. Entered once, never recalculated.
--
--   Moving with the market. Price, traded value, return since announcement,
--   and flow measured in days of ADVT. These drift from the moment the note is
--   written, and they are the columns that decide whether a name is worth
--   acting on.
--
-- So the estimate is stored as given and attributed, and everything that moves
-- is refreshed from Upstox candles rather than frozen at entry. That is what
-- keeps a six-week-old review readable in week five.

-- NSE and BSE instrument master, from Upstox's public instruments file.
--
-- Needed because a research table names a stock the way Bloomberg does -
-- "MEESHO IS" - and every market data call here needs an instrument_key like
-- "NSE_EQ|INE0ONG01011". Guessing the mapping by stripping the country suffix
-- is right most of the time, which is the worst possible hit rate: the misses
-- are silent and land on whichever names happen to be renamed.
create table if not exists public.nse_instruments (
  instrument_key text primary key,
  exchange text not null,
  segment text,
  trading_symbol text not null,
  name text,
  isin text,
  instrument_type text,
  lot_size integer,
  tick_size numeric,
  -- When this row was last seen in the published file. A symbol that stops
  -- appearing has been delisted or renamed, and a stale mapping pointed at a
  -- dead instrument_key returns empty candles rather than an error.
  refreshed_at timestamptz not null default now()
);

create index if not exists nse_instruments_symbol_idx
  on public.nse_instruments (upper(trading_symbol), exchange);
create index if not exists nse_instruments_isin_idx
  on public.nse_instruments (isin);

-- One row per index review.
create table if not exists public.index_rebalance_events (
  id uuid primary key default gen_random_uuid(),
  provider text not null check (provider in ('FTSE', 'MSCI', 'SP', 'NSE', 'Other')),
  index_name text not null,
  market text not null default 'india',
  -- Announcement and effective are different dates and the gap is the whole
  -- trade. Flows print on the effective date; positioning happens between.
  announced_on date not null,
  effective_on date,
  source_url text,
  notes text,
  created_at timestamptz not null default now(),
  unique (provider, index_name, announced_on)
);

-- One row per affected stock.
create table if not exists public.index_rebalance_entries (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null references public.index_rebalance_events(id) on delete cascade,

  -- As written in the source, kept verbatim so a row can always be traced back
  -- to the line it came from even after the mapping below is corrected.
  source_ticker text not null,
  company_name text,
  sector text,

  -- Resolved against nse_instruments. Nullable on purpose: an unresolved row
  -- is still worth storing and showing, it simply cannot be priced. Dropping
  -- it would hide the failure instead of surfacing it.
  instrument_key text references public.nse_instruments(instrument_key),

  change_type text not null,

  -- The estimate, exactly as published, in millions of US dollars. Negative is
  -- an outflow. Stored rather than derived - this is somebody's model output,
  -- not a fact, and re-deriving it would silently substitute a different one.
  net_passive_flow_usd_mn numeric,
  -- Whose estimate, and as of when. Two houses on the same event disagree, and
  -- the disagreement is more informative than either number alone.
  estimate_source text,
  estimate_as_of date,

  -- As-of values from the source, kept for comparison against what the nightly
  -- refresh computes. A large divergence means the mapping is wrong.
  source_mkt_cap_usd_mn numeric,
  source_advt_usd_mn numeric,

  est_next_earnings date,
  ex_dividend_on date,

  created_at timestamptz not null default now(),
  unique (event_id, source_ticker)
);

create index if not exists index_rebalance_entries_event_idx
  on public.index_rebalance_entries (event_id);
create index if not exists index_rebalance_entries_instrument_idx
  on public.index_rebalance_entries (instrument_key);

-- Everything that moves, recomputed rather than stored at entry.
--
-- Separate from the entry so a refresh never rewrites the entered data. A bad
-- refresh should leave the source numbers untouched and visibly unrefreshed,
-- not overwrite an analyst's input with a bad candle.
create table if not exists public.index_rebalance_quotes (
  entry_id uuid primary key references public.index_rebalance_entries(id) on delete cascade,
  last_price_inr numeric,
  -- Average daily traded value over the trailing window, converted to USD so
  -- it is comparable with the flow estimate. Both must be in one currency or
  -- the days-of-ADVT ratio is meaningless.
  advt_3m_usd_mn numeric,
  usd_inr numeric,
  -- Flow divided by current ADVT: how many sessions of normal volume the
  -- passive trade represents. The single most useful column in the table, and
  -- the one that decays fastest, because ADVT moves as the event approaches.
  days_of_advt numeric,
  return_since_announced_pct numeric,
  refreshed_at timestamptz not null default now(),
  -- Why a row has no numbers. An unpriced row must say whether it was never
  -- attempted, could not be mapped, or came back empty.
  refresh_note text
);

alter table public.nse_instruments enable row level security;
alter table public.index_rebalance_events enable row level security;
alter table public.index_rebalance_entries enable row level security;
alter table public.index_rebalance_quotes enable row level security;

comment on table public.index_rebalance_entries is
  'Index review constituent changes. Flow estimates are stored as published and attributed via estimate_source; they are third-party model output, not derived here.';
