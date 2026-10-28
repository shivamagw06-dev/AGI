-- AGIB Intelligence Layer V2 — optional durable store (in-memory remains default).
-- Soft additive schema; does not redesign FAA/FRE/CAE.

create schema if not exists ail;

create table if not exists ail.evidence_ledger (
  evidence_id text primary key,
  claim text not null,
  company text,
  ticker text,
  source text not null,
  url text,
  page integer,
  section text,
  retrieved_at timestamptz not null default now(),
  connector text not null default 'ail',
  authority_score integer not null default 5,
  confidence double precision not null default 0.7,
  content_hash text not null,
  document_version text,
  validation_status text not null default 'registered',
  verified_against jsonb not null default '[]'::jsonb,
  metadata jsonb not null default '{}'::jsonb
);

create unique index if not exists ail_evidence_content_hash_uidx
  on ail.evidence_ledger (content_hash);

create index if not exists ail_evidence_ticker_idx
  on ail.evidence_ledger (ticker);

create table if not exists ail.dossier_versions (
  dossier_id text primary key,
  ticker text not null,
  company text not null,
  version integer not null,
  fields jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  supersedes text references ail.dossier_versions(dossier_id)
);

create index if not exists ail_dossier_ticker_idx
  on ail.dossier_versions (ticker, version desc);

create table if not exists ail.events (
  event_id text primary key,
  company text not null,
  ticker text not null,
  ts timestamptz not null default now(),
  category text not null,
  importance integer not null default 5,
  evidence_ids jsonb not null default '[]'::jsonb,
  confidence double precision not null default 0.6,
  previous_value text,
  new_value text,
  impact text,
  metadata jsonb not null default '{}'::jsonb
);

create index if not exists ail_events_ticker_idx
  on ail.events (ticker, ts desc);

create table if not exists ail.thesis_versions (
  thesis_id text primary key,
  ticker text not null,
  company text not null,
  version integer not null,
  bull jsonb not null,
  base jsonb not null,
  bear jsonb not null,
  explanation jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  supersedes text references ail.thesis_versions(thesis_id)
);

create table if not exists ail.predictions (
  prediction_id text primary key,
  ticker text not null,
  company text not null,
  version integer not null,
  model_version text not null,
  prediction_date timestamptz not null default now(),
  review_date date,
  scenario jsonb not null,
  distributions jsonb not null,
  sensitivity jsonb not null default '{}'::jsonb,
  inputs jsonb not null default '{}'::jsonb,
  evidence_ids jsonb not null default '[]'::jsonb,
  confidence double precision not null default 0.55,
  outcome jsonb
);

create index if not exists ail_predictions_ticker_idx
  on ail.predictions (ticker, version desc);

create table if not exists ail.timeline_entries (
  entry_id text primary key,
  ticker text not null,
  company text not null,
  year integer,
  ts timestamptz not null default now(),
  title text not null,
  category text not null default 'update',
  evidence_ids jsonb not null default '[]'::jsonb,
  event_id text
);

create table if not exists ail.graph_edges (
  edge_id text primary key,
  src text not null,
  rel text not null,
  dst text not null,
  evidence_ids jsonb not null default '[]'::jsonb,
  weight double precision not null default 1.0
);

create unique index if not exists ail_graph_edge_uidx
  on ail.graph_edges (src, rel, dst);

create table if not exists ail.audit_records (
  audit_id text primary key,
  query text not null,
  ticker text,
  evidence_ids jsonb not null default '[]'::jsonb,
  thesis_version text,
  prediction_version text,
  dossier_version text,
  reasoning_inputs jsonb not null default '{}'::jsonb,
  confidence double precision not null default 0,
  created_at timestamptz not null default now()
);

alter table ail.evidence_ledger enable row level security;
alter table ail.dossier_versions enable row level security;
alter table ail.events enable row level security;
alter table ail.thesis_versions enable row level security;
alter table ail.predictions enable row level security;
alter table ail.timeline_entries enable row level security;
alter table ail.graph_edges enable row level security;
alter table ail.audit_records enable row level security;
