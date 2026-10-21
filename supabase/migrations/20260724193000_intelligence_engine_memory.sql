-- AGI Intelligence Engine memory layer
-- Research runs, evidence archive, report embeddings (pgvector)

create extension if not exists vector;

create table if not exists public.intelligence_research_runs (
  run_id text primary key,
  desk text not null,
  status text not null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists intelligence_research_runs_desk_updated_idx
  on public.intelligence_research_runs (desk, updated_at desc);

create table if not exists public.intelligence_evidence_items (
  evidence_id text primary key,
  run_id text not null references public.intelligence_research_runs(run_id) on delete cascade,
  agent_id text,
  claim text not null,
  source_id text not null,
  source_type text not null,
  snippet text,
  url text,
  reliability numeric,
  fetched_at timestamptz,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists intelligence_evidence_items_run_idx
  on public.intelligence_evidence_items (run_id);

create table if not exists public.intelligence_report_embeddings (
  run_id text primary key references public.intelligence_research_runs(run_id) on delete cascade,
  desk text not null,
  title text,
  content text not null,
  embedding vector(1536),
  created_at timestamptz not null default now()
);

create table if not exists public.intelligence_predictions (
  prediction_id text primary key,
  run_id text not null,
  statement text not null,
  horizon text not null,
  actual_outcome text,
  accuracy numeric,
  success_reason text,
  failure_reason text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

alter table public.intelligence_research_runs enable row level security;
alter table public.intelligence_evidence_items enable row level security;
alter table public.intelligence_report_embeddings enable row level security;
alter table public.intelligence_predictions enable row level security;

-- Public read optional; writes via service role only.
do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'intelligence_research_runs'
      and policyname = 'intelligence_research_runs_public_read'
  ) then
    create policy intelligence_research_runs_public_read
      on public.intelligence_research_runs for select to anon, authenticated using (true);
  end if;
end $$;
