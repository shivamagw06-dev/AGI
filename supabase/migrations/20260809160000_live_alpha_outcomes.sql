-- Forward outcome lifecycle for AGI Live Alpha Signals.

alter table public.live_alpha_signals
  add column if not exists direction text check (direction in ('positive', 'negative')),
  add column if not exists market_regime text,
  add column if not exists price_at_signal numeric check (price_at_signal is null or price_at_signal > 0),
  add column if not exists nifty_at_signal numeric check (nifty_at_signal is null or nifty_at_signal > 0),
  add column if not exists sector_at_signal numeric check (sector_at_signal is null or sector_at_signal > 0),
  add column if not exists volume_ratio numeric check (volume_ratio is null or volume_ratio >= 0),
  add column if not exists vwap_deviation numeric,
  add column if not exists oi_change numeric,
  add column if not exists beta numeric not null default 1;

create table if not exists public.live_alpha_signal_outcomes (
  id uuid primary key default gen_random_uuid(),
  signal_id uuid not null references public.live_alpha_signals(id) on delete cascade,
  horizon text not null check (horizon in ('5m', '15m', '30m', '1h', 'close', 'next_day', '5d')),
  due_at timestamptz not null,
  observed_at timestamptz,
  status text not null default 'pending' check (status in ('pending', 'completed', 'missed')),
  attempt_count integer not null default 0 check (attempt_count >= 0),
  last_error text,
  price_at_signal numeric not null check (price_at_signal > 0),
  nifty_at_signal numeric not null check (nifty_at_signal > 0),
  sector_at_signal numeric not null check (sector_at_signal > 0),
  future_price numeric check (future_price is null or future_price > 0),
  future_nifty numeric check (future_nifty is null or future_nifty > 0),
  future_sector numeric check (future_sector is null or future_sector > 0),
  stock_return_pct numeric,
  market_return_pct numeric,
  sector_return_pct numeric,
  directional_return_pct numeric,
  market_adjusted_alpha_pct numeric,
  sector_adjusted_alpha_pct numeric,
  estimated_cost_bps numeric not null default 0 check (estimated_cost_bps >= 0),
  net_alpha_pct numeric,
  positive_outcome boolean,
  created_at timestamptz not null default now(),
  unique (signal_id, horizon),
  check (status <> 'completed' or (observed_at is not null and future_price is not null and net_alpha_pct is not null))
);

create index if not exists live_alpha_outcomes_pending_due_idx
  on public.live_alpha_signal_outcomes (due_at)
  where status = 'pending';
create index if not exists live_alpha_outcomes_signal_horizon_idx
  on public.live_alpha_signal_outcomes (signal_id, horizon);

alter table public.live_alpha_signal_outcomes enable row level security;

comment on table public.live_alpha_signal_outcomes is
  'Scheduled and completed forward measurements for research-only alpha signals.';
