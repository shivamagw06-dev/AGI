-- Knowledge Intelligence Platform (KIP) P0
-- Institutional memory layer for AGI. No model fine-tuning.

create table if not exists public.kip_documents (
  document_id text primary key,
  lineage_id text not null,
  version integer not null default 1,
  title text not null default '',
  author text not null default '',
  source text not null default '',
  document_type text not null,
  broker text not null default '',
  language text not null default 'en',
  document_date date,
  supersedes text,
  superseded_by text,
  content text not null default '',
  cleaned_content text not null default '',
  ocr_applied boolean not null default false,
  investment jsonb not null default '{}'::jsonb,
  research jsonb not null default '{}'::jsonb,
  knowledge jsonb not null default '{}'::jsonb,
  pipeline_stages jsonb not null default '[]'::jsonb,
  knowledge_version text not null default 'kip-v1.0.1',
  immutable boolean not null default true,
  created_at timestamptz not null default now()
);

create index if not exists kip_documents_lineage_idx
  on public.kip_documents (lineage_id, version);

create index if not exists kip_documents_type_idx
  on public.kip_documents (document_type);

create index if not exists kip_documents_date_idx
  on public.kip_documents (document_date desc);

create table if not exists public.kip_chunks (
  chunk_id text primary key,
  document_id text not null references public.kip_documents(document_id),
  lineage_id text not null,
  version integer not null default 1,
  ordinal integer not null default 0,
  text text not null,
  tokens jsonb not null default '[]'::jsonb,
  embedding vector(256),
  tickers jsonb not null default '[]'::jsonb,
  themes jsonb not null default '[]'::jsonb,
  sectors jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists kip_chunks_document_idx
  on public.kip_chunks (document_id, ordinal);

create table if not exists public.kip_graph_nodes (
  node_id text primary key,
  kind text not null,
  label text not null,
  attributes jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

create index if not exists kip_graph_nodes_kind_idx
  on public.kip_graph_nodes (kind);

create table if not exists public.kip_graph_edges (
  edge_id text primary key,
  source text not null,
  target text not null,
  relation text not null,
  document_id text,
  weight double precision not null default 1.0,
  created_at timestamptz not null default now()
);

create index if not exists kip_graph_edges_source_idx
  on public.kip_graph_edges (source);

create index if not exists kip_graph_edges_target_idx
  on public.kip_graph_edges (target);

create table if not exists public.kip_timeline_events (
  event_id text primary key,
  ticker text not null,
  event_date date not null,
  event_type text not null,
  title text not null default '',
  document_id text,
  source text not null default '',
  summary text not null default '',
  created_at timestamptz not null default now()
);

create index if not exists kip_timeline_ticker_date_idx
  on public.kip_timeline_events (ticker, event_date);
