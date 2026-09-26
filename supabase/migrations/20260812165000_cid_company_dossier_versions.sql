create table if not exists public.cid_company_dossier_versions (
  id uuid primary key,
  ticker text not null,
  company_name text not null,
  version integer not null,
  generator_version text,
  model text,
  generated_at timestamptz not null default now(),
  coverage_score double precision,
  coverage_grade text,
  dossier jsonb not null,
  created_at timestamptz not null default now(),
  unique (ticker, version)
);

create index if not exists cid_company_dossier_versions_latest_idx
  on public.cid_company_dossier_versions (ticker, version desc);

alter table public.cid_company_dossier_versions enable row level security;

comment on table public.cid_company_dossier_versions is
  'Immutable, server-written versions of evidence-grounded company dossiers used by Ask AGI.';
