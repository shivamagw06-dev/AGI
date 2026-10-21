-- Reasoning & Research Synthesis Platform (RSP) P0
-- Institutional reasoning packages. No fine-tuning. No engine redesign.

create table if not exists public.rsp_reasoning_packages (
  reasoning_id text primary key,
  question text not null,
  ticker text,
  confidence double precision not null default 0,
  reasoning_version text not null default 'rsp-v1.0.1',
  answer_policy text not null default 'rsp_reasons_before_llm',
  consensus jsonb not null default '{}'::jsonb,
  research_continuity jsonb not null default '{}'::jsonb,
  synthesis jsonb not null default '{}'::jsonb,
  contradictions jsonb not null default '[]'::jsonb,
  validation jsonb not null default '{}'::jsonb,
  engine_inputs jsonb not null default '{}'::jsonb,
  pipeline_stages jsonb not null default '[]'::jsonb,
  house_view jsonb,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists rsp_reasoning_ticker_idx
  on public.rsp_reasoning_packages (ticker, created_at desc);

create table if not exists public.rsp_evidence_statements (
  evidence_id text primary key,
  reasoning_id text not null references public.rsp_reasoning_packages(reasoning_id),
  statement text not null,
  kind text not null,
  source text not null default '',
  reliability double precision not null default 0.5,
  freshness double precision not null default 0.5,
  confidence double precision not null default 0.5,
  score double precision not null default 0.5,
  supporting_documents jsonb not null default '[]'::jsonb,
  contradicting_documents jsonb not null default '[]'::jsonb,
  engine_support jsonb not null default '[]'::jsonb,
  house_view_alignment text not null default 'unknown',
  cluster text not null default '',
  created_at timestamptz not null default now()
);

create index if not exists rsp_evidence_reasoning_idx
  on public.rsp_evidence_statements (reasoning_id);
