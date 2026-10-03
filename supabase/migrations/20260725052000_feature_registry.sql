-- WS03 Feature Registry (WBS FEAT-001)
-- Engineered features only; research engines consume these rows, never recompute indicators.

create table if not exists public.feature_registry (
  feature_id text primary key,
  category text not null,
  description text not null,
  owner text not null,
  formula_version text not null,
  dependencies jsonb not null default '[]'::jsonb,
  inputs jsonb not null default '[]'::jsonb,
  refresh_frequency text not null,
  confidence double precision not null default 1.0,
  source text not null,
  unit text,
  polarity text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.feature_pit (
  feature_id text not null references public.feature_registry (feature_id),
  symbol text not null default '',
  as_of date not null,
  available_at timestamptz not null,
  formula_version text not null,
  value jsonb,
  confidence double precision not null default 1.0,
  quality_flag text not null default 'ok',
  source text not null,
  input_hash text,
  metadata jsonb not null default '{}'::jsonb,
  primary key (feature_id, symbol, as_of, formula_version)
);

create index if not exists feature_pit_symbol_asof_idx
  on public.feature_pit (symbol, as_of desc);

create index if not exists feature_pit_feature_asof_idx
  on public.feature_pit (feature_id, as_of desc);

create table if not exists public.feature_snapshots (
  snapshot_id text primary key,
  as_of date not null,
  universe_id text,
  symbol text,
  created_at timestamptz not null default now(),
  payload jsonb not null
);
