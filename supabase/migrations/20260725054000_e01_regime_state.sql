-- E01 Macro & Regime Engine persistence (WBS E01-001–005 P0)
-- EngineState envelope stored as jsonb; threshold-only model_version.

create table if not exists public.e01_feature_snapshot (
  id uuid primary key default gen_random_uuid(),
  as_of date not null,
  feature_id text not null,
  value double precision,
  z_value double precision,
  meta jsonb not null default '{}'::jsonb,
  unique (as_of, feature_id)
);

create index if not exists e01_feature_asof_idx
  on public.e01_feature_snapshot (as_of desc);

create table if not exists public.e01_regime_state (
  id uuid primary key default gen_random_uuid(),
  as_of date not null unique,
  macro_score double precision not null,
  primary_regime text not null,
  axes jsonb not null,
  confidence double precision not null,
  risk_level text not null,
  size_multiplier double precision not null,
  vol_target double precision not null,
  weight_adjustments jsonb not null,
  top_features jsonb not null default '[]'::jsonb,
  falsifiers jsonb not null default '[]'::jsonb,
  submodels jsonb not null default '{}'::jsonb,
  model_version text not null,
  input_hash text not null,
  state jsonb not null,
  created_at timestamptz not null default now()
);

create index if not exists e01_regime_primary_idx
  on public.e01_regime_state (primary_regime, as_of desc);

create table if not exists public.e01_regime_current (
  id text primary key default 'current',
  state_id uuid references public.e01_regime_state (id),
  state jsonb not null,
  updated_at timestamptz not null default now()
);
