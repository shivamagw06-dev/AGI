-- FRE v1 — Finance Retrieval Engine persistence (optional; runtime is in-memory first).
-- Additive soft-wire. Does not redesign KIP tables.

create extension if not exists vector;

create table if not exists fre_documents (
  document_id text primary key,
  title text not null,
  url text,
  source text,
  document_type text,
  organisation text,
  company text,
  symbol text,
  published_at text,
  financial_year text,
  quarter text,
  region text default 'IN',
  language text default 'en',
  content_type text,
  raw_text text,
  checksum text unique,
  authority int default 2,
  tier int default 6,
  version int default 1,
  metadata jsonb default '{}'::jsonb,
  retrieved_at timestamptz default now(),
  created_at timestamptz default now()
);

create table if not exists fre_chunks (
  chunk_id text primary key,
  document_id text references fre_documents(document_id) on delete cascade,
  text text not null,
  heading text,
  section text,
  page int,
  company text,
  symbol text,
  document_type text,
  source text,
  published_at text,
  reporting_period text,
  authority int default 2,
  confidence numeric,
  token_estimate int,
  embedding vector(256),
  metadata jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);

create index if not exists fre_chunks_document_idx on fre_chunks(document_id);
create index if not exists fre_chunks_company_idx on fre_chunks(company);
create index if not exists fre_chunks_symbol_idx on fre_chunks(symbol);
create index if not exists fre_documents_symbol_idx on fre_documents(symbol);
create index if not exists fre_documents_type_idx on fre_documents(document_type);

create table if not exists fre_evidence (
  evidence_id text primary key,
  claim text not null,
  source text,
  document_id text,
  chunk_id text,
  page int,
  section text,
  company text,
  symbol text,
  document_type text,
  published_at text,
  confidence numeric,
  authority int,
  supporting_chunk_ids jsonb default '[]'::jsonb,
  contradictory_evidence_ids jsonb default '[]'::jsonb,
  validation_status text default 'unvalidated',
  created_at timestamptz default now()
);

create index if not exists fre_evidence_company_idx on fre_evidence(company);
create index if not exists fre_evidence_symbol_idx on fre_evidence(symbol);

create table if not exists fre_graph_nodes (
  node_id text primary key,
  label text not null,
  kind text default 'entity',
  company text,
  metadata jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);

create table if not exists fre_graph_edges (
  edge_id text primary key,
  source_id text references fre_graph_nodes(node_id) on delete cascade,
  target_id text references fre_graph_nodes(node_id) on delete cascade,
  relation text not null,
  confidence numeric,
  evidence_ids jsonb default '[]'::jsonb,
  created_at timestamptz default now()
);
