-- Normalized Upstox V3 observations and collector health for Live Alpha Signals.

create table if not exists public.live_market_snapshots (
  id bigint generated always as identity primary key,
  instrument_key text not null,
  observed_at timestamptz not null,
  exchange_timestamp timestamptz,
  ltp numeric not null check (ltp > 0),
  previous_close numeric check (previous_close is null or previous_close > 0),
  last_traded_quantity numeric check (last_traded_quantity is null or last_traded_quantity >= 0),
  average_traded_price numeric check (average_traded_price is null or average_traded_price > 0),
  cumulative_volume numeric check (cumulative_volume is null or cumulative_volume >= 0),
  open_interest numeric check (open_interest is null or open_interest >= 0),
  implied_volatility numeric check (implied_volatility is null or implied_volatility >= 0),
  best_bid numeric,
  best_ask numeric,
  spread_bps numeric check (spread_bps is null or spread_bps >= 0),
  feed_latency_ms integer check (feed_latency_ms is null or feed_latency_ms >= 0),
  -- Populated by the trigger below. A trigger is used instead of a generated
  -- column because Supabase/PostgreSQL rejects timezone-aware truncation in a
  -- generated expression as non-immutable.
  minute_bucket timestamptz,
  raw_factors jsonb not null default '{}'::jsonb check (jsonb_typeof(raw_factors) = 'object'),
  unique (instrument_key, observed_at)
);

create or replace function public.set_live_market_snapshot_minute_bucket()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  new.minute_bucket := date_trunc('minute', new.observed_at at time zone 'UTC') at time zone 'UTC';
  return new;
end;
$$;

drop trigger if exists set_live_market_snapshot_minute_bucket on public.live_market_snapshots;
create trigger set_live_market_snapshot_minute_bucket
before insert or update of observed_at on public.live_market_snapshots
for each row execute function public.set_live_market_snapshot_minute_bucket();

create index if not exists live_market_snapshots_instrument_time_idx
  on public.live_market_snapshots (instrument_key, observed_at desc);
create index if not exists live_market_snapshots_minute_idx
  on public.live_market_snapshots (minute_bucket, instrument_key);

create table if not exists public.live_market_feed_health (
  id bigint generated always as identity primary key,
  observed_at timestamptz not null default now(),
  status text not null check (status in ('idle', 'authorizing', 'connected', 'reconnecting', 'stopped', 'degraded')),
  subscribed_instruments integer not null check (subscribed_instruments >= 0),
  messages bigint not null default 0 check (messages >= 0),
  decode_errors bigint not null default 0 check (decode_errors >= 0),
  reconnects integer not null default 0 check (reconnects >= 0),
  last_message_at timestamptz,
  stale_instruments integer not null default 0 check (stale_instruments >= 0),
  diagnostics jsonb not null default '{}'::jsonb check (jsonb_typeof(diagnostics) = 'object')
);

alter table public.live_market_snapshots enable row level security;
alter table public.live_market_feed_health enable row level security;

comment on table public.live_market_snapshots is
  'Normalized research-only observations decoded from the Upstox V3 Protobuf stream.';
