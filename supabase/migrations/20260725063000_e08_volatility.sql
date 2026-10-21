-- E08 Volatility & Options Intelligence persistence (WBS E08-001–005 P0)
-- P0 realized/hist vol only. No gamma / dealer / surface tables.

create table if not exists public.e08_feature_snapshot (
  id uuid primary key default gen_random_uuid(),
  as_of date not null,
  symbol text not null,
  feature_id text not null,
  value double precision,
  meta jsonb not null default '{}'::jsonb,
  unique (as_of, symbol, feature_id)
);

create index if not exists e08_feature_symbol_asof_idx
  on public.e08_feature_snapshot (symbol, as_of desc);

create table if not exists public.e08_vol_state (
  id uuid primary key default gen_random_uuid(),
  as_of date not null,
  symbol text not null,
  universe_id text not null,
  sector_id text,
  metrics jsonb not null default '{}'::jsonb,
  realized_vol double precision not null,
  historical_vol double precision not null,
  vol_regime text not null,
  expansion boolean not null,
  compression boolean not null,
  expansion_score double precision not null,
  compression_score double precision not null,
  expected_move double precision,
  composite_score double precision not null,
  label text not null,
  confidence double precision not null,
  model_version text not null,
  formula_id text not null,
  input_hash text,
  state jsonb not null,
  created_at timestamptz not null default now(),
  unique (as_of, symbol, universe_id)
);

create index if not exists e08_vol_state_symbol_asof_idx
  on public.e08_vol_state (symbol, as_of desc);
