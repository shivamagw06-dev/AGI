-- E13 Equity Fundamental L/S Engine persistence (WBS E13-001–005 P0)
-- P0 fundamentals only. No ML / revisions / moat tables.

create table if not exists public.e13_feature_snapshot (
  id uuid primary key default gen_random_uuid(),
  as_of date not null,
  symbol text not null,
  feature_id text not null,
  value double precision,
  meta jsonb not null default '{}'::jsonb,
  unique (as_of, symbol, feature_id)
);

create index if not exists e13_feature_symbol_asof_idx
  on public.e13_feature_snapshot (symbol, as_of desc);

create table if not exists public.e13_fundamentals (
  id uuid primary key default gen_random_uuid(),
  as_of date not null,
  symbol text not null,
  universe_id text not null,
  sector_id text,
  metrics jsonb not null default '{}'::jsonb,
  quality_score double precision not null,
  value_score double precision not null,
  growth_score double precision not null,
  balance_sheet_score double precision not null,
  composite_score double precision not null,
  label text not null,
  side text not null,
  confidence double precision not null,
  model_version text not null,
  formula_id text not null,
  input_hash text,
  state jsonb not null,
  created_at timestamptz not null default now(),
  unique (as_of, symbol, universe_id)
);

create index if not exists e13_fundamentals_symbol_asof_idx
  on public.e13_fundamentals (symbol, as_of desc);
