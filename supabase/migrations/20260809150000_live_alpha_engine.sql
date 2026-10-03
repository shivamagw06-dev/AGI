-- AGI Live Alpha Engine — research-only run and signal store.
-- Observations are append-only; there are deliberately no order or position fields.

create table if not exists public.live_alpha_runs (
  id uuid primary key default gen_random_uuid(),
  engine text not null check (engine in (
    'cross_sectional_momentum_v1',
    'volume_liquidity_anomaly_v1',
    'opening_range_expansion_v1',
    'intraday_mean_reversion_v1',
    'derivatives_positioning_v1',
    'regime_composite_v1'
  )),
  as_of timestamptz not null,
  market_session date not null,
  universe_size integer not null check (universe_size > 0),
  research_only boolean not null default true check (research_only),
  execution_enabled boolean not null default false check (not execution_enabled),
  feed_source text not null default 'upstox_v3',
  feed_latency_ms integer check (feed_latency_ms is null or feed_latency_ms >= 0),
  config jsonb not null default '{}'::jsonb check (jsonb_typeof(config) = 'object'),
  diagnostics jsonb not null default '{}'::jsonb check (jsonb_typeof(diagnostics) = 'object'),
  created_at timestamptz not null default now(),
  unique (engine, as_of)
);

create table if not exists public.live_alpha_signals (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references public.live_alpha_runs(id) on delete cascade,
  symbol text not null check (symbol = upper(symbol)),
  instrument_key text,
  sector text,
  rank integer not null check (rank > 0),
  classification text not null check (classification in (
    'positive_research_candidate', 'negative_research_candidate', 'neutral', 'filtered'
  )),
  alpha_z numeric(8,4) not null,
  signal_quality_score numeric(5,2) not null check (signal_quality_score between 0 and 100),
  signal_quality_label text not null check (signal_quality_label in (
    'ignore', 'weak', 'moderate', 'strong', 'very_strong', 'exceptional'
  )),
  empirical_confidence_score numeric(5,2) check (empirical_confidence_score between 0 and 100),
  comparable_observations integer not null default 0 check (comparable_observations >= 0),
  liquidity_ok boolean not null,
  factor_values jsonb not null check (jsonb_typeof(factor_values) = 'object'),
  explanation jsonb not null default '[]'::jsonb check (jsonb_typeof(explanation) = 'array'),
  created_at timestamptz not null default now(),
  unique (run_id, symbol),
  unique (run_id, rank)
);

create index if not exists live_alpha_runs_engine_as_of_idx
  on public.live_alpha_runs (engine, as_of desc);
create index if not exists live_alpha_signals_run_alpha_idx
  on public.live_alpha_signals (run_id, alpha_z desc);
create index if not exists live_alpha_signals_symbol_created_idx
  on public.live_alpha_signals (symbol, created_at desc);

create table if not exists public.live_alpha_validation_metrics (
  id uuid primary key default gen_random_uuid(),
  engine text not null,
  horizon text not null check (horizon in ('5m', '15m', '30m', '1h', 'close', 'next_day', '5d')),
  regime text not null default 'all',
  evaluated_through timestamptz not null,
  sample_size integer not null check (sample_size >= 0),
  validation_status text not null check (validation_status in ('insufficient_sample', 'eligible', 'validated', 'rejected')),
  metrics jsonb not null check (jsonb_typeof(metrics) = 'object'),
  created_at timestamptz not null default now(),
  unique (engine, horizon, regime, evaluated_through)
);

create index if not exists live_alpha_validation_engine_horizon_idx
  on public.live_alpha_validation_metrics (engine, horizon, evaluated_through desc);

alter table public.live_alpha_runs enable row level security;
alter table public.live_alpha_signals enable row level security;
alter table public.live_alpha_validation_metrics enable row level security;

comment on table public.live_alpha_runs is
  'Research-only evaluations from AGI live alpha factor engines; never an execution ledger.';
comment on table public.live_alpha_signals is
  'Cross-sectional research rankings and factor evidence; contains no order instructions.';
