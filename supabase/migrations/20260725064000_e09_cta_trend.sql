-- E09 CTA Trend Engine persistence (WBS E09-001–005 P0)
-- P0 single-name trend signals only. No breakout / cross-asset / ML tables.

create table if not exists public.e09_feature_snapshot (
  id uuid primary key default gen_random_uuid(),
  as_of date not null,
  symbol text not null,
  feature_id text not null,
  value double precision,
  meta jsonb not null default '{}'::jsonb,
  unique (as_of, symbol, feature_id)
);

create index if not exists e09_feature_symbol_asof_idx
  on public.e09_feature_snapshot (symbol, as_of desc);

create table if not exists public.e09_trend_state (
  id uuid primary key default gen_random_uuid(),
  as_of date not null,
  symbol text not null,
  universe_id text not null,
  sector_id text,
  metrics jsonb not null default '{}'::jsonb,
  short_trend double precision not null,
  medium_trend double precision not null,
  long_trend double precision not null,
  ts_momentum double precision not null,
  vol_scaled_signal double precision not null,
  persistence double precision not null,
  exhaustion double precision not null,
  composite_score double precision not null,
  side text not null,
  label text not null,
  confidence double precision not null,
  model_version text not null,
  formula_id text not null,
  input_hash text,
  state jsonb not null,
  created_at timestamptz not null default now(),
  unique (as_of, symbol, universe_id)
);

create index if not exists e09_trend_state_symbol_asof_idx
  on public.e09_trend_state (symbol, as_of desc);
