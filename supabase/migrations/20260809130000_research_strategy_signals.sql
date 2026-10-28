-- AGI Phase 2 — Groww Cloud research signal storage.
--
-- Stores compact, research-only outputs from the two active strategies:
--   * agi_sector_rotation_v1
--   * agi_equity_opportunity_v1
--
-- Tables are append-only and private by default. The service role used by the
-- ingestion API bypasses RLS; no anon/authenticated policies are created here.

create table if not exists public.research_strategy_runs (
  id uuid primary key default gen_random_uuid(),
  strategy text not null check (
    strategy in ('agi_sector_rotation_v1', 'agi_equity_opportunity_v1')
  ),
  run_id text not null unique,
  as_of timestamptz not null,
  received_at timestamptz not null default now(),
  source text not null default 'groww_cloud' check (source = 'groww_cloud'),
  schema_version text not null default '1.0',
  research_only boolean not null default true check (research_only),
  status text not null default 'received' check (
    status in ('received', 'validated', 'processed', 'rejected')
  ),
  coverage integer not null default 0 check (coverage >= 0),
  error_count integer not null default 0 check (error_count >= 0),
  payload_hash text,
  rejection_reason text,
  raw_payload jsonb not null,
  created_at timestamptz not null default now(),
  processed_at timestamptz,
  check (run_id like strategy || ':%'),
  check (jsonb_typeof(raw_payload) = 'object')
);

create index if not exists research_strategy_runs_strategy_as_of_idx
  on public.research_strategy_runs (strategy, as_of desc);

create index if not exists research_strategy_runs_status_received_idx
  on public.research_strategy_runs (status, received_at desc);

create unique index if not exists research_strategy_runs_payload_hash_idx
  on public.research_strategy_runs (payload_hash)
  where payload_hash is not null;

create table if not exists public.sector_rotation_signals (
  id uuid primary key default gen_random_uuid(),
  strategy_run_id uuid not null
    references public.research_strategy_runs(id) on delete cascade,
  sector text not null check (sector = upper(sector)),
  rank integer not null check (rank > 0),
  score numeric(5,1) not null check (score between 0 and 100),
  close numeric,
  return_5d numeric,
  return_20d numeric,
  return_60d numeric,
  relative_20d numeric,
  relative_60d numeric,
  volatility_20d numeric check (volatility_20d is null or volatility_20d >= 0),
  max_drawdown numeric check (max_drawdown is null or max_drawdown <= 0),
  rotation text not null check (
    rotation in ('leading', 'improving', 'weakening', 'lagging')
  ),
  risk text not null check (risk in ('low', 'moderate', 'high')),
  factors jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (strategy_run_id, sector),
  unique (strategy_run_id, rank),
  check (jsonb_typeof(factors) = 'object')
);

create index if not exists sector_rotation_signals_sector_created_idx
  on public.sector_rotation_signals (sector, created_at desc);

create index if not exists sector_rotation_signals_run_score_idx
  on public.sector_rotation_signals (strategy_run_id, score desc);

create index if not exists sector_rotation_signals_rotation_score_idx
  on public.sector_rotation_signals (rotation, score desc);

create table if not exists public.equity_opportunity_signals (
  id uuid primary key default gen_random_uuid(),
  strategy_run_id uuid not null
    references public.research_strategy_runs(id) on delete cascade,
  symbol text not null check (symbol = upper(symbol)),
  signal text not null check (signal in ('research_candidate', 'risk_review')),
  rank integer check (rank is null or rank > 0),
  score numeric(5,1) not null check (score between 0 and 100),
  close numeric,
  return_20d numeric,
  return_60d numeric,
  relative_20d numeric,
  relative_60d numeric,
  volatility_20d numeric check (volatility_20d is null or volatility_20d >= 0),
  volume_ratio numeric check (volume_ratio is null or volume_ratio >= 0),
  trend text not null check (trend in ('positive', 'mixed', 'negative')),
  volume_confirmation boolean not null default false,
  risk text not null check (risk in ('low', 'moderate', 'high')),
  reasons jsonb not null default '[]'::jsonb,
  factors jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (strategy_run_id, symbol, signal),
  check (signal <> 'research_candidate' or rank is not null),
  check (jsonb_typeof(reasons) = 'array'),
  check (jsonb_typeof(factors) = 'object')
);

create unique index if not exists equity_opportunity_candidate_rank_idx
  on public.equity_opportunity_signals (strategy_run_id, rank)
  where signal = 'research_candidate';

create index if not exists equity_opportunity_signals_symbol_created_idx
  on public.equity_opportunity_signals (symbol, created_at desc);

create index if not exists equity_opportunity_signals_run_score_idx
  on public.equity_opportunity_signals (strategy_run_id, score desc);

create index if not exists equity_opportunity_signals_signal_score_idx
  on public.equity_opportunity_signals (signal, score desc);

alter table public.research_strategy_runs enable row level security;
alter table public.sector_rotation_signals enable row level security;
alter table public.equity_opportunity_signals enable row level security;

comment on table public.research_strategy_runs is
  'Immutable Groww Cloud strategy-run envelope and original JSON payload.';
comment on table public.sector_rotation_signals is
  'Normalized sector rankings produced by agi_sector_rotation_v1.';
comment on table public.equity_opportunity_signals is
  'Normalized research candidates and deterioration warnings produced by agi_equity_opportunity_v1.';

