-- E04 Statistical Arbitrage & Relative Value persistence (WBS E04-001–005 P0)
-- P0 OLS/EG/half-life only. No Kalman / dynamic hedge / ETF basis / ML tables.

create table if not exists public.e04_feature_snapshot (
  id uuid primary key default gen_random_uuid(),
  as_of date not null,
  pair_id text not null,
  feature_id text not null,
  value double precision,
  meta jsonb not null default '{}'::jsonb,
  unique (as_of, pair_id, feature_id)
);

create index if not exists e04_feature_pair_asof_idx
  on public.e04_feature_snapshot (pair_id, as_of desc);

create table if not exists public.e04_rv_state (
  id uuid primary key default gen_random_uuid(),
  as_of date not null,
  pair_id text not null,
  universe_id text not null,
  leg_a text not null,
  leg_b text not null,
  sector_id text,
  hedge_alpha double precision not null,
  hedge_beta double precision not null,
  r_squared double precision not null,
  spread double precision not null,
  z_score double precision not null,
  cointegrated boolean not null,
  adf_stat double precision not null,
  half_life double precision,
  mispricing_score double precision not null,
  mean_reversion_signal double precision not null,
  composite_score double precision not null,
  label text not null,
  side text not null,
  confidence double precision not null,
  discovery text not null,
  model_version text not null,
  formula_id text not null,
  input_hash text,
  state jsonb not null,
  created_at timestamptz not null default now(),
  unique (as_of, pair_id, universe_id)
);

create index if not exists e04_rv_state_pair_asof_idx
  on public.e04_rv_state (pair_id, as_of desc);
