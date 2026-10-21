-- E02 Factor & Style Engine persistence (WBS E02-001–005 P0)
-- P0 factors only: Momentum, LowVol, Size, Liquidity, Quality, Value.

create table if not exists public.e02_feature_snapshot (
  id uuid primary key default gen_random_uuid(),
  as_of date not null,
  symbol text not null,
  feature_id text not null,
  value double precision,
  meta jsonb not null default '{}'::jsonb,
  unique (as_of, symbol, feature_id)
);

create index if not exists e02_feature_symbol_asof_idx
  on public.e02_feature_snapshot (symbol, as_of desc);

create table if not exists public.e02_exposures (
  id uuid primary key default gen_random_uuid(),
  as_of date not null,
  symbol text not null,
  universe_id text not null,
  sector_id text,
  scores jsonb not null,
  loadings jsonb not null,
  composite_score double precision not null,
  dominant_factor text not null,
  factor_confidence double precision not null,
  model_version text not null,
  input_hash text,
  state jsonb not null,
  created_at timestamptz not null default now(),
  unique (as_of, symbol, universe_id)
);

create index if not exists e02_exposures_symbol_asof_idx
  on public.e02_exposures (symbol, as_of desc);
