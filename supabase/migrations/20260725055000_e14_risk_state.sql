-- E14 Risk & Crowding Overlay persistence (WBS E14-001–005 P0)
-- Rule-based firm risk prior + assessments; no ML/Bayes.

create table if not exists public.e14_feature_snapshot (
  id uuid primary key default gen_random_uuid(),
  as_of date not null,
  feature_id text not null,
  value double precision,
  meta jsonb not null default '{}'::jsonb,
  unique (as_of, feature_id)
);

create index if not exists e14_feature_asof_idx
  on public.e14_feature_snapshot (as_of desc);

create table if not exists public.e14_risk_state (
  id uuid primary key default gen_random_uuid(),
  as_of date not null unique,
  risk_score double precision not null,
  risk_level text not null,
  crowding_score double precision not null,
  liquidity_score double precision not null,
  tail_risk_score double precision not null,
  size_multiplier double precision not null,
  confidence_adjustment double precision not null,
  playbook text not null,
  gate text not null,
  taxonomy_scores jsonb not null,
  engine_weight_adjustments jsonb not null,
  model_version text not null,
  input_hash text not null,
  state jsonb not null,
  created_at timestamptz not null default now()
);

create index if not exists e14_risk_level_idx
  on public.e14_risk_state (risk_level, as_of desc);

create table if not exists public.e14_risk_current (
  id text primary key default 'current',
  state_id uuid references public.e14_risk_state (id),
  state jsonb not null,
  updated_at timestamptz not null default now()
);

create table if not exists public.e14_assessments (
  assessment_id uuid primary key,
  target_type text not null,
  target_id text not null,
  as_of date not null,
  risk_score double precision not null,
  gate text not null,
  size_multiplier double precision not null,
  confidence_adjustment double precision not null,
  payload jsonb not null,
  created_at timestamptz not null default now()
);

create index if not exists e14_assessments_target_idx
  on public.e14_assessments (target_type, target_id, as_of desc);
