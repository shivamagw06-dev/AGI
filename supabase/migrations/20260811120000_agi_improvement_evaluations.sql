-- Ask AGI improvement worker — append-only evaluation persistence.
-- The isolated AGI improvement worker writes here; never mutates production financial tables.

create table if not exists public.agi_improvement_sessions (
  session_id text primary key,
  version text not null,
  mode text not null default 'execute',
  endpoint_host text,
  started_questions integer not null default 0,
  completed integer not null default 0,
  passed integer not null default 0,
  failed integer not null default 0,
  pass_rate numeric(6, 2),
  average_score numeric(6, 2),
  critical_failures integer not null default 0,
  average_latency_ms integer,
  model_calls integer not null default 0,
  input_tokens integer not null default 0,
  output_tokens integer not null default 0,
  total_tokens integer not null default 0,
  estimated_api_cost_usd numeric(12, 6),
  report jsonb not null default '{}'::jsonb,
  finished_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists public.agi_improvement_evaluations (
  id bigserial primary key,
  session_id text not null references public.agi_improvement_sessions (session_id) on delete cascade,
  question_id text,
  ticker text,
  sector text,
  difficulty text,
  kind text,
  status text not null,
  latency_ms integer,
  score numeric(6, 2),
  passed boolean,
  critical_failure boolean not null default false,
  root_causes jsonb not null default '[]'::jsonb,
  record jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.agi_improvement_learning_events (
  event_id text primary key,
  session_id text not null references public.agi_improvement_sessions (session_id) on delete cascade,
  status text not null default 'DIAGNOSIS_REQUIRED',
  root_causes jsonb not null default '[]'::jsonb,
  critical_failures jsonb not null default '[]'::jsonb,
  affected_subsystem text,
  record jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists agi_improvement_sessions_finished_idx
  on public.agi_improvement_sessions (finished_at desc nulls last);

create index if not exists agi_improvement_evaluations_session_idx
  on public.agi_improvement_evaluations (session_id, created_at desc);

create index if not exists agi_improvement_learning_events_session_idx
  on public.agi_improvement_learning_events (session_id, created_at desc);

alter table public.agi_improvement_sessions enable row level security;
alter table public.agi_improvement_evaluations enable row level security;
alter table public.agi_improvement_learning_events enable row level security;
