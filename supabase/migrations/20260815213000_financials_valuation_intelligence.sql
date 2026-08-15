-- Governed sector valuation knowledge. Company outputs remain in existing valuation stores.
create table if not exists public.sector_valuation_models (
  sector_id text primary key,
  sector_name text not null,
  parent_sector text not null default 'FINANCIALS',
  subsector text not null,
  active_version text not null,
  validation_status text not null check (validation_status in ('PROPOSED','VALIDATED','TRUSTED','QUARANTINED','EXPIRED','SUPERSEDED')),
  confidence numeric not null check (confidence between 0 and 1),
  effective_date date not null,
  last_reviewed timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.sector_valuation_model_versions (
  sector_id text not null references public.sector_valuation_models(sector_id),
  version text not null,
  model_payload jsonb not null,
  content_hash text not null,
  created_by text not null,
  created_at timestamptz not null default now(),
  supersedes_version text,
  primary key (sector_id, version)
);

create table if not exists public.sector_valuation_evidence (
  evidence_id uuid primary key default gen_random_uuid(),
  sector_id text not null references public.sector_valuation_models(sector_id),
  version text not null,
  knowledge_key text not null,
  source_type text not null,
  source_id text not null,
  source_date date,
  available_at timestamptz not null,
  evidence_payload jsonb not null default '{}'::jsonb,
  validation_status text not null default 'PROPOSED' check (validation_status in ('PROPOSED','VALIDATED','TRUSTED','QUARANTINED','REJECTED')),
  confidence numeric not null default 0 check (confidence between 0 and 1),
  created_at timestamptz not null default now(),
  unique (sector_id, version, knowledge_key, source_id, available_at)
);

create table if not exists public.sector_valuation_certifications (
  certification_id uuid primary key default gen_random_uuid(),
  sector_id text not null references public.sector_valuation_models(sector_id),
  model_version text not null,
  certification_status text not null check (certification_status in ('NOT_STARTED','IN_PROGRESS','FAILED','PASSED','EXPIRED')),
  gates jsonb not null default '{}'::jsonb,
  passed_gates integer not null default 0,
  total_gates integer not null default 20,
  evaluated_companies text[] not null default '{}',
  evidence_cutoff timestamptz,
  reviewer text,
  certified_at timestamptz,
  created_at timestamptz not null default now()
);

create index if not exists idx_sector_valuation_evidence_pit on public.sector_valuation_evidence(sector_id, available_at desc);
create index if not exists idx_sector_valuation_certifications_status on public.sector_valuation_certifications(sector_id, certification_status);

alter table public.sector_valuation_models enable row level security;
alter table public.sector_valuation_model_versions enable row level security;
alter table public.sector_valuation_evidence enable row level security;
alter table public.sector_valuation_certifications enable row level security;

comment on table public.sector_valuation_models is 'Governed sector valuation curriculum; models cannot self-approve.';
comment on table public.sector_valuation_certifications is 'Twenty-gate sector certification; no implied production approval.';
