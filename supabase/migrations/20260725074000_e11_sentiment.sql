-- E11 Sentiment & Alternative Data persistence (EPIC-015 / E11-001–005 P0)
-- News soft voter only. Social/transcripts/LLM/ML/altdata off.

create table if not exists public.e11_entity_map (
  entity_id text primary key,
  symbol text not null,
  name text,
  aliases jsonb not null default '[]'::jsonb,
  sector_id text,
  confidence double precision not null default 0.9,
  updated_at timestamptz not null default now(),
  unique (symbol)
);

create index if not exists e11_entity_map_symbol_idx
  on public.e11_entity_map (symbol);

create table if not exists public.e11_state_current (
  id uuid primary key default gen_random_uuid(),
  as_of date not null,
  symbol text not null,
  universe_id text not null,
  entity_id text not null,
  news_score double precision not null,
  composite_score double precision not null,
  reliability_weight double precision not null,
  decay_weight double precision not null,
  freshness_hours double precision not null,
  soft_voter_weight double precision not null,
  social_weight_cap double precision not null default 0.05,
  social_enabled boolean not null default false,
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

create index if not exists e11_state_symbol_asof_idx
  on public.e11_state_current (symbol, as_of desc);
