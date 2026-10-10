-- Research Management System (RMS) P0
-- Institutional research lifecycle. No CMS/website/engine redesign.

create table if not exists public.rms_research (
  research_id text primary key,
  title text not null,
  status text not null,
  owner text not null default '',
  reviewer text not null default '',
  version integer not null default 1,
  tickers jsonb not null default '[]'::jsonb,
  sectors jsonb not null default '[]'::jsonb,
  themes jsonb not null default '[]'::jsonb,
  idea_summary text not null default '',
  request_brief text not null default '',
  draft_body text not null default '',
  evidence_package jsonb not null default '{}'::jsonb,
  reasoning_package jsonb not null default '{}'::jsonb,
  reasoning_id text,
  engine_snapshot jsonb not null default '{}'::jsonb,
  house_view jsonb,
  prediction_horizon text not null default '90d',
  prediction_ids jsonb not null default '[]'::jsonb,
  kip_document_ids jsonb not null default '[]'::jsonb,
  publishing_history jsonb not null default '[]'::jsonb,
  publication_artifacts jsonb not null default '[]'::jsonb,
  compliance jsonb not null default '{}'::jsonb,
  assignments jsonb not null default '{}'::jsonb,
  metadata jsonb not null default '{}'::jsonb,
  rms_version text not null default 'rms-v1.0.1',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  published_at timestamptz
);

create index if not exists rms_research_status_idx
  on public.rms_research (status);

create index if not exists rms_research_owner_idx
  on public.rms_research (owner);

create index if not exists rms_research_published_idx
  on public.rms_research (published_at desc);
