-- Append-only company research memory and material thesis changes.
create table if not exists public.research_memory_states (
  id uuid primary key default gen_random_uuid(),
  state_key text not null unique,
  confluence_event_id uuid not null unique references public.research_confluence_events(id) on delete cascade,
  symbol text not null, captured_at timestamptz not null,
  fundamental_score numeric, valuation_score numeric, sector_score numeric,
  eod_confirmation numeric, live_confirmation numeric, catalyst_score numeric,
  confluence_class text not null, research_priority numeric, market_regime text, sector text,
  key_bull_evidence jsonb not null default '[]'::jsonb check (jsonb_typeof(key_bull_evidence) = 'array'),
  key_bear_evidence jsonb not null default '[]'::jsonb check (jsonb_typeof(key_bear_evidence) = 'array'),
  risks jsonb not null default '[]'::jsonb check (jsonb_typeof(risks) = 'array'),
  catalysts jsonb not null default '[]'::jsonb check (jsonb_typeof(catalysts) = 'array'),
  source_snapshot jsonb not null check (jsonb_typeof(source_snapshot) = 'object'),
  research_only boolean not null default true check (research_only),
  created_at timestamptz not null default now()
);

create table if not exists public.research_memory_changes (
  id uuid primary key default gen_random_uuid(),
  symbol text not null,
  current_state_id uuid not null unique references public.research_memory_states(id) on delete cascade,
  prior_state_id uuid references public.research_memory_states(id) on delete set null,
  detected_at timestamptz not null,
  change_types jsonb not null default '[]'::jsonb check (jsonb_typeof(change_types) = 'array'),
  field_changes jsonb not null default '{}'::jsonb check (jsonb_typeof(field_changes) = 'object'),
  interpretation text not null,
  material boolean not null default false,
  created_at timestamptz not null default now()
);

create index if not exists research_memory_states_symbol_time_idx on public.research_memory_states (symbol, captured_at desc);
create index if not exists research_memory_changes_symbol_time_idx on public.research_memory_changes (symbol, detected_at desc);
create index if not exists research_memory_changes_material_time_idx on public.research_memory_changes (detected_at desc) where material;

alter table public.research_memory_states enable row level security;
alter table public.research_memory_changes enable row level security;

comment on table public.research_memory_states is 'Append-only, dated AGI research states reconstructed from immutable confluence events.';
comment on table public.research_memory_changes is 'Deterministic thesis-change classifications between consecutive company research states.';
