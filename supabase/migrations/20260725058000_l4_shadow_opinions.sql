-- L4 Composite Intelligence P0 Shadow persistence (WBS L4-001–005)
-- Shadow tables only. Never mutates E03 / production research.

create table if not exists public.l4_opinion (
  id uuid primary key default gen_random_uuid(),
  as_of date not null,
  symbol text not null,
  universe_id text not null,
  label text not null,
  composite_score double precision not null,
  confidence double precision not null,
  shadow boolean not null default true,
  primary_mode boolean not null default false,
  model_version text not null,
  weight_set_id text not null,
  opinion jsonb not null,
  state jsonb not null,
  input_hash text,
  created_at timestamptz not null default now(),
  unique (as_of, symbol, universe_id)
);

create index if not exists l4_opinion_symbol_asof_idx
  on public.l4_opinion (symbol, as_of desc);

create table if not exists public.l4_shadow_comparison (
  id uuid primary key default gen_random_uuid(),
  as_of date not null,
  symbol text not null,
  legacy_label text not null,
  legacy_confidence double precision not null,
  l4_label text not null,
  l4_confidence double precision not null,
  agreement boolean not null,
  disagreement_reason text,
  dominant_driver text,
  evidence_summary text not null,
  report jsonb not null,
  model_version text not null,
  created_at timestamptz not null default now(),
  unique (as_of, symbol)
);

create index if not exists l4_shadow_symbol_asof_idx
  on public.l4_shadow_comparison (symbol, as_of desc);
