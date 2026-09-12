-- E03 Cross-Sectional Quant Engine persistence (WBS E03-001–005 P0/M0)
-- SM_AGI_TECH production parity only; composite / XS / ML deferred.

create table if not exists public.e03_alpha (
  id uuid primary key default gen_random_uuid(),
  as_of date not null,
  symbol text not null,
  universe_id text not null,
  agi_tech_score double precision not null,
  composite_alpha_score double precision not null,
  label text not null,
  confidence_pct integer not null,
  confidence double precision not null,
  model_version text not null,
  submodel_id text not null default 'SM_AGI_TECH',
  indicators jsonb not null default '{}'::jsonb,
  state jsonb not null,
  input_hash text,
  created_at timestamptz not null default now(),
  unique (as_of, symbol, universe_id)
);

create index if not exists e03_alpha_symbol_asof_idx
  on public.e03_alpha (symbol, as_of desc);

create table if not exists public.e03_parity_audit (
  id uuid primary key default gen_random_uuid(),
  as_of date not null,
  generated_at timestamptz not null,
  n_symbols integer not null,
  agreement_rate double precision not null,
  bucket_agreement_rate double precision not null,
  confidence_agreement_rate double precision not null,
  mean_drift double precision not null,
  max_drift double precision not null,
  within_0_1_rate double precision not null,
  passed boolean not null,
  report jsonb not null,
  model_version text not null,
  created_at timestamptz not null default now()
);

create index if not exists e03_parity_asof_idx
  on public.e03_parity_audit (as_of desc);
