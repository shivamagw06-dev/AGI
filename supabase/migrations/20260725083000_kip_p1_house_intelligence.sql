-- KIP P1 — Continuous Knowledge Acquisition & House Intelligence
-- Extends institutional memory: auto-ingest channels, house view, predictions.

alter table if exists public.kip_documents
  add column if not exists article_id text,
  add column if not exists research_type text not null default '';

create index if not exists kip_documents_article_id_idx
  on public.kip_documents (article_id);

create table if not exists public.kip_predictions (
  prediction_id text primary key,
  ticker text not null,
  document_id text not null,
  article_id text,
  thesis text not null default '',
  target_price text not null default '',
  expected_return text not null default '',
  catalysts jsonb not null default '[]'::jsonb,
  sector text not null default '',
  analyst text not null default '',
  predicted_at date not null,
  horizon_days integer not null default 90,
  status text not null default 'open',
  outcome_return double precision,
  hit boolean,
  thesis_success boolean,
  catalyst_hit boolean,
  evaluated_at date,
  notes text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists kip_predictions_ticker_idx
  on public.kip_predictions (ticker, predicted_at desc);

create table if not exists public.kip_house_views (
  ticker text primary key,
  current_document_id text,
  payload jsonb not null default '{}'::jsonb,
  research_confidence double precision not null default 0,
  prediction_accuracy double precision,
  knowledge_version text not null default 'kip-v1.0.1-p1',
  last_updated timestamptz not null default now()
);
