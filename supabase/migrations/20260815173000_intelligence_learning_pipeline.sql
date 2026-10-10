-- Durable, resumable AGI universal intelligence-learning layer.
-- Teacher output remains proposed until validation promotes it; source documents
-- and the existing research knowledge registry remain canonical evidence.

create table if not exists public.intelligence_learning_jobs (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.research_knowledge_documents(id) on delete cascade,
  pipeline_version text not null default 'universal-learning-v1',
  status text not null default 'queued' check (status in ('queued','running','validated','quarantined','failed','paused')),
  current_stage text not null default 'classification',
  completed_stages jsonb not null default '[]'::jsonb,
  stage_results jsonb not null default '{}'::jsonb,
  model_roles jsonb not null default '{}'::jsonb,
  attempts integer not null default 0,
  max_attempts integer not null default 3,
  priority smallint not null default 5 check (priority between 1 and 9),
  lease_owner text,
  lease_expires_at timestamptz,
  last_error text,
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (document_id, pipeline_version)
);

create table if not exists public.intelligence_evidence_records (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.research_knowledge_documents(id) on delete cascade,
  source_locator jsonb not null default '{}'::jsonb,
  evidence_text text not null,
  evidence_type text not null default 'source_passage',
  publication_date timestamptz,
  effective_date timestamptz,
  source_authority numeric(5,4) not null default 0.5 check (source_authority between 0 and 1),
  content_hash text,
  created_at timestamptz not null default now()
);

create table if not exists public.intelligence_industry_kpis (
  id uuid primary key default gen_random_uuid(),
  industry_key text not null,
  sub_industry text,
  kpi_key text not null,
  name text not null,
  definition text,
  formula text,
  why_it_matters text,
  indicator_type text check (indicator_type in ('leading','lagging','coincident','mixed')),
  expected_direction text,
  typical_lag text,
  evidence_ids uuid[] not null default '{}',
  confidence numeric(5,4) not null default 0.5 check (confidence between 0 and 1),
  status text not null default 'proposed' check (status in ('proposed','approved','quarantined','superseded')),
  valid_from timestamptz,
  valid_to timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (industry_key, sub_industry, kpi_key, valid_from)
);

create table if not exists public.intelligence_causal_chains (
  id uuid primary key default gen_random_uuid(),
  document_id uuid references public.research_knowledge_documents(id) on delete set null,
  industry_key text,
  trigger text not null,
  nodes jsonb not null default '[]'::jsonb,
  edges jsonb not null default '[]'::jsonb,
  conditions jsonb not null default '[]'::jsonb,
  counter_effects jsonb not null default '[]'::jsonb,
  time_horizon text,
  evidence_ids uuid[] not null default '{}',
  confidence numeric(5,4) not null default 0.5 check (confidence between 0 and 1),
  status text not null default 'proposed' check (status in ('proposed','approved','quarantined','superseded')),
  valid_from timestamptz,
  valid_to timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.intelligence_financial_impacts (
  id uuid primary key default gen_random_uuid(),
  document_id uuid references public.research_knowledge_documents(id) on delete set null,
  causal_chain_id uuid references public.intelligence_causal_chains(id) on delete set null,
  entity_key text,
  trigger text not null,
  statement_type text not null check (statement_type in ('income_statement','balance_sheet','cash_flow','returns','valuation')),
  metric_key text not null,
  direction text check (direction in ('increase','decrease','mixed','uncertain')),
  directness text not null default 'indirect' check (directness in ('direct','indirect')),
  calculation_method text,
  inputs jsonb not null default '{}'::jsonb,
  quantified_value numeric,
  quantified_unit text,
  evidence_ids uuid[] not null default '{}',
  confidence numeric(5,4) not null default 0.5 check (confidence between 0 and 1),
  status text not null default 'proposed' check (status in ('proposed','approved','quarantined','superseded')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.intelligence_theses (
  id uuid primary key default gen_random_uuid(),
  thesis_key text not null unique,
  entity_key text,
  industry_key text,
  title text not null,
  lifecycle_status text not null default 'monitoring' check (lifecycle_status in ('draft','monitoring','strengthened','weakened','invalidated','closed')),
  current_version integer not null default 1,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.intelligence_thesis_versions (
  id uuid primary key default gen_random_uuid(),
  thesis_id uuid not null references public.intelligence_theses(id) on delete cascade,
  version integer not null,
  document_id uuid references public.research_knowledge_documents(id) on delete set null,
  thesis_text text not null,
  supporting_conditions jsonb not null default '[]'::jsonb,
  invalidation_conditions jsonb not null default '[]'::jsonb,
  risks jsonb not null default '[]'::jsonb,
  catalysts jsonb not null default '[]'::jsonb,
  scenarios jsonb not null default '[]'::jsonb,
  time_horizon text,
  evidence_ids uuid[] not null default '{}',
  confidence numeric(5,4) not null default 0.5 check (confidence between 0 and 1),
  status text not null default 'proposed' check (status in ('proposed','approved','quarantined','superseded')),
  created_at timestamptz not null default now(),
  unique (thesis_id, version)
);

create table if not exists public.intelligence_monitoring_indicators (
  id uuid primary key default gen_random_uuid(),
  thesis_id uuid references public.intelligence_theses(id) on delete cascade,
  entity_key text,
  industry_key text,
  indicator_key text not null,
  name text not null,
  why_it_matters text,
  expected_direction text,
  frequency text,
  trigger_condition text,
  source_preference jsonb not null default '[]'::jsonb,
  confidence numeric(5,4) not null default 0.5 check (confidence between 0 and 1),
  status text not null default 'proposed' check (status in ('proposed','approved','quarantined','inactive')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.intelligence_outcome_records (
  id uuid primary key default gen_random_uuid(),
  thesis_id uuid references public.intelligence_theses(id) on delete set null,
  causal_chain_id uuid references public.intelligence_causal_chains(id) on delete set null,
  prediction text not null,
  predicted_at timestamptz not null,
  evaluation_due_at timestamptz,
  actual_outcome text,
  actual_value jsonb,
  error_analysis text,
  failed_assumptions jsonb not null default '[]'::jsonb,
  relationships_held jsonb not null default '[]'::jsonb,
  relationships_failed jsonb not null default '[]'::jsonb,
  review_status text not null default 'pending' check (review_status in ('pending','machine_reviewed','human_reviewed','rejected')),
  evaluated_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.intelligence_learning_examples (
  id uuid primary key default gen_random_uuid(),
  question text not null,
  context jsonb not null default '{}'::jsonb,
  retrieved_evidence jsonb not null default '[]'::jsonb,
  industry_knowledge jsonb not null default '{}'::jsonb,
  causal_knowledge jsonb not null default '{}'::jsonb,
  financial_data jsonb not null default '{}'::jsonb,
  reasoning jsonb not null default '{}'::jsonb,
  answer text not null,
  critic_result jsonb not null default '{}'::jsonb,
  human_review jsonb not null default '{}'::jsonb,
  outcome_record_id uuid references public.intelligence_outcome_records(id) on delete set null,
  quality_score numeric(5,4) check (quality_score between 0 and 1),
  training_eligible boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists intelligence_learning_jobs_queue_idx on public.intelligence_learning_jobs (status, priority, created_at);
create index if not exists intelligence_causal_chains_lookup_idx on public.intelligence_causal_chains (industry_key, trigger, status);
create index if not exists intelligence_financial_impacts_lookup_idx on public.intelligence_financial_impacts (entity_key, metric_key, status);
create index if not exists intelligence_thesis_versions_lookup_idx on public.intelligence_thesis_versions (thesis_id, version desc);
create index if not exists intelligence_monitoring_lookup_idx on public.intelligence_monitoring_indicators (thesis_id, indicator_key, status);
create index if not exists intelligence_outcomes_due_idx on public.intelligence_outcome_records (review_status, evaluation_due_at);

alter table public.intelligence_learning_jobs enable row level security;
alter table public.intelligence_evidence_records enable row level security;
alter table public.intelligence_industry_kpis enable row level security;
alter table public.intelligence_causal_chains enable row level security;
alter table public.intelligence_financial_impacts enable row level security;
alter table public.intelligence_theses enable row level security;
alter table public.intelligence_thesis_versions enable row level security;
alter table public.intelligence_monitoring_indicators enable row level security;
alter table public.intelligence_outcome_records enable row level security;
alter table public.intelligence_learning_examples enable row level security;

comment on table public.intelligence_learning_jobs is 'Resumable universal learning pipeline; teacher proposals require validation before promotion.';
comment on table public.intelligence_learning_examples is 'Reviewed evaluation/distillation corpus; training_eligible is never set solely by model output.';
