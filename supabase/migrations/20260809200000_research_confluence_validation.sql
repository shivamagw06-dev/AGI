-- Immutable Research Confluence snapshots and their forward validation ledger.
create table if not exists public.research_confluence_events (
  id uuid primary key default gen_random_uuid(),
  event_key text not null unique,
  symbol text not null,
  captured_at timestamptz not null,
  classification text not null check (classification in ('HIGH_CONFLUENCE','CONFIRMED','WATCH','CONTRADICTION','TACTICAL_ONLY','VALUATION_ONLY','MOMENTUM_WITHOUT_VALUE','DEVELOPING')),
  fundamental_score numeric, valuation_score numeric, eod_confirmation numeric,
  live_confirmation numeric, catalyst_score numeric,
  leadership numeric, activity numeric, breakout numeric, dislocation numeric, positioning numeric,
  research_priority numeric, market_regime text, sector text,
  instrument_key text not null, benchmark_instrument_key text not null, sector_instrument_key text not null,
  price_at_signal numeric not null check (price_at_signal > 0),
  benchmark_at_signal numeric not null check (benchmark_at_signal > 0),
  sector_index_at_signal numeric not null check (sector_index_at_signal > 0),
  completeness jsonb not null default '{}'::jsonb,
  evidence_snapshot jsonb not null check (jsonb_typeof(evidence_snapshot) = 'object'),
  research_only boolean not null default true check (research_only),
  created_at timestamptz not null default now()
);

create table if not exists public.research_confluence_outcomes (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null references public.research_confluence_events(id) on delete cascade,
  horizon text not null check (horizon in ('5m','15m','30m','60m','close','1d','5d','20d')),
  due_at timestamptz not null, observed_at timestamptz,
  status text not null default 'pending' check (status in ('pending','completed','missed')),
  attempt_count integer not null default 0, last_error text,
  future_price numeric, future_benchmark numeric, future_sector numeric,
  stock_return_pct numeric, benchmark_return_pct numeric, sector_return_pct numeric,
  excess_return_pct numeric, sector_adjusted_alpha_pct numeric, positive_excess boolean,
  created_at timestamptz not null default now(),
  unique (event_id, horizon),
  check (status <> 'completed' or (observed_at is not null and future_price is not null and excess_return_pct is not null))
);

create index if not exists research_confluence_events_class_time_idx on public.research_confluence_events (classification, captured_at desc);
create index if not exists research_confluence_events_symbol_time_idx on public.research_confluence_events (symbol, captured_at desc);
create index if not exists research_confluence_outcomes_pending_idx on public.research_confluence_outcomes (due_at) where status = 'pending';
create index if not exists research_confluence_outcomes_horizon_idx on public.research_confluence_outcomes (horizon, status);

alter table public.research_confluence_events enable row level security;
alter table public.research_confluence_outcomes enable row level security;

comment on table public.research_confluence_events is 'Immutable, research-only evidence snapshots used to validate Research Confluence classifications.';
comment on table public.research_confluence_outcomes is 'Forward stock, benchmark and sector outcomes for confluence events.';
