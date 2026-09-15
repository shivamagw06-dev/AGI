-- Prior-session minute-of-day baselines for point-in-time-safe volume surprise.

create unique index if not exists live_market_snapshots_instrument_minute_uidx
  on public.live_market_snapshots (instrument_key, minute_bucket);

create table if not exists public.live_volume_baselines (
  instrument_key text not null,
  minute_of_session integer not null check (minute_of_session between 0 and 375),
  expected_cumulative_volume numeric not null check (expected_cumulative_volume >= 0),
  sample_sessions integer not null check (sample_sessions >= 5),
  calculated_through date not null,
  method text not null default 'median_prior_sessions' check (method = 'median_prior_sessions'),
  updated_at timestamptz not null default now(),
  primary key (instrument_key, minute_of_session)
);

create index if not exists live_volume_baselines_minute_idx
  on public.live_volume_baselines (minute_of_session, instrument_key);

alter table public.live_volume_baselines enable row level security;

comment on table public.live_volume_baselines is
  'Median cumulative-volume curve by instrument and NSE session minute, built only from prior sessions.';
