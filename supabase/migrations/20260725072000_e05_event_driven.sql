-- E05 Event-Driven & Special Situations persistence (WBS E05-001–005 P0)
-- P0 calendar / CA / surprise / decay only. No deal-prob / transcripts / ML tables.

create table if not exists public.e05_event_object (
  id uuid primary key default gen_random_uuid(),
  event_id text not null,
  symbol text not null,
  event_type text not null,
  event_time timestamptz not null,
  as_of date not null,
  actual double precision,
  consensus double precision,
  guidance_delta double precision,
  importance double precision,
  meta jsonb not null default '{}'::jsonb,
  unique (event_id, as_of)
);

create index if not exists e05_event_symbol_time_idx
  on public.e05_event_object (symbol, event_time desc);

create index if not exists e05_event_type_idx
  on public.e05_event_object (event_type, event_time desc);

create table if not exists public.e05_event_state (
  id uuid primary key default gen_random_uuid(),
  as_of date not null,
  symbol text not null,
  universe_id text not null,
  primary_event_type text,
  event_importance double precision not null,
  surprise_score double precision not null,
  decay_factor double precision not null,
  composite_score double precision not null,
  expected_event_impact double precision not null,
  days_since_event double precision,
  days_until_event double precision,
  label text not null,
  side text not null,
  confidence double precision not null,
  discovery text not null,
  model_version text not null,
  formula_id text not null,
  input_hash text,
  state jsonb not null,
  created_at timestamptz not null default now(),
  unique (as_of, symbol, universe_id)
);

create index if not exists e05_event_state_symbol_asof_idx
  on public.e05_event_state (symbol, as_of desc);
