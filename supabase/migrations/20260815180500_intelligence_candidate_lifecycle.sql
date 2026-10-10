-- Preserve every extracted lesson as candidate knowledge and separate automated
-- validation from promotion into AGI's trusted knowledge graph.

create table if not exists public.intelligence_learning_candidates (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null unique references public.intelligence_learning_jobs(id) on delete cascade,
  document_id uuid not null references public.research_knowledge_documents(id) on delete cascade,
  pipeline_version text not null,
  payload jsonb not null default '{}'::jsonb,
  deterministic_validation jsonb not null default '{}'::jsonb,
  critic_result jsonb not null default '{}'::jsonb,
  lifecycle_status text not null default 'proposed'
    check (lifecycle_status in ('proposed','validated','trusted','quarantined','superseded')),
  validation_reasons jsonb not null default '[]'::jsonb,
  evidence_ids uuid[] not null default '{}',
  teacher_model text,
  teacher_response_id text,
  teacher_usage jsonb not null default '{}'::jsonb,
  trusted_by text,
  trusted_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists intelligence_learning_candidates_review_idx
  on public.intelligence_learning_candidates (lifecycle_status, updated_at desc);

alter table public.intelligence_learning_candidates enable row level security;

comment on table public.intelligence_learning_candidates is
  'Complete teacher proposals and validation receipts. Only trusted candidates may be promoted into durable Ask AGI knowledge.';

