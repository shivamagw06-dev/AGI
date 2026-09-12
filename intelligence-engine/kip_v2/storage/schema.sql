-- KIP v2 — Institutional Knowledge Intelligence
-- Canonical Postgres + pgvector schema for production deployment (e.g. Supabase).
--
-- This file is the source of truth that kip_v2/storage/postgres_store.py
-- assumes exists. It is NOT auto-applied by application code (this repo has
-- no live DDL-executing connection to the configured Supabase project — only
-- a REST/PostgREST credential pair). Apply it once via the Supabase SQL
-- editor / psql / a migration tool, then set KIP_V2_DATABASE_URL to a
-- Postgres connection string pointing at the same database and the
-- application will use it transparently in place of the default SQLite store.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS kip_v2_documents (
    document_id     TEXT PRIMARY KEY,
    company_id      TEXT NOT NULL,
    doc_type        TEXT NOT NULL,
    period          TEXT,
    title           TEXT,
    source          TEXT,
    page_count      INTEGER,
    published_at    TEXT,
    ingested_at     DOUBLE PRECISION,
    version         INTEGER
);
CREATE INDEX IF NOT EXISTS idx_kip_v2_documents_company ON kip_v2_documents(company_id);

CREATE TABLE IF NOT EXISTS kip_v2_paragraphs (
    paragraph_id    TEXT PRIMARY KEY,
    document_id     TEXT NOT NULL REFERENCES kip_v2_documents(document_id),
    company_id      TEXT NOT NULL,
    section         TEXT,
    page            INTEGER,
    idx             INTEGER,
    text            TEXT,
    is_table        BOOLEAN,
    entities        JSONB,
    importance_score DOUBLE PRECISION,
    embedding       VECTOR(256),
    evidence_hash   TEXT
);
CREATE INDEX IF NOT EXISTS idx_kip_v2_paragraphs_doc ON kip_v2_paragraphs(document_id);
CREATE INDEX IF NOT EXISTS idx_kip_v2_paragraphs_company ON kip_v2_paragraphs(company_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_kip_v2_paragraphs_evhash ON kip_v2_paragraphs(document_id, evidence_hash);
-- ANN index for semantic retrieval at scale (Module 9):
CREATE INDEX IF NOT EXISTS idx_kip_v2_paragraphs_embedding
    ON kip_v2_paragraphs USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE TABLE IF NOT EXISTS kip_v2_facts (
    fact_id             TEXT PRIMARY KEY,
    company_id          TEXT NOT NULL,
    category            TEXT NOT NULL,
    key                 TEXT NOT NULL,
    value               JSONB,
    period              TEXT,
    unit                TEXT,
    currency            TEXT,
    confidence          DOUBLE PRECISION,
    evidence            JSONB NOT NULL,
    source_document_id  TEXT NOT NULL,
    timestamp           DOUBLE PRECISION,
    version             INTEGER,
    status              TEXT,
    superseded_by       TEXT,
    extra               JSONB
);
CREATE INDEX IF NOT EXISTS idx_kip_v2_facts_company ON kip_v2_facts(company_id, category, status);
CREATE INDEX IF NOT EXISTS idx_kip_v2_facts_key ON kip_v2_facts(company_id, key);

CREATE TABLE IF NOT EXISTS kip_v2_graph_nodes (
    node_id     TEXT PRIMARY KEY,
    node_type   TEXT,
    name        TEXT,
    attributes  JSONB
);

CREATE TABLE IF NOT EXISTS kip_v2_graph_edges (
    edge_id         TEXT PRIMARY KEY,
    source_id       TEXT REFERENCES kip_v2_graph_nodes(node_id),
    target_id       TEXT REFERENCES kip_v2_graph_nodes(node_id),
    relation        TEXT,
    confidence      DOUBLE PRECISION,
    evidence_hash   TEXT
);
CREATE INDEX IF NOT EXISTS idx_kip_v2_edges_source ON kip_v2_graph_edges(source_id);
CREATE INDEX IF NOT EXISTS idx_kip_v2_edges_target ON kip_v2_graph_edges(target_id);

CREATE TABLE IF NOT EXISTS kip_v2_deltas (
    delta_id        TEXT PRIMARY KEY,
    company_id      TEXT,
    category        TEXT,
    key             TEXT,
    change_type     TEXT,
    from_period     TEXT,
    to_period       TEXT,
    old_value       JSONB,
    new_value       JSONB,
    old_evidence    JSONB,
    new_evidence    JSONB,
    magnitude_pct   DOUBLE PRECISION,
    detected_at     DOUBLE PRECISION
);
CREATE INDEX IF NOT EXISTS idx_kip_v2_deltas_company ON kip_v2_deltas(company_id);

CREATE TABLE IF NOT EXISTS kip_v2_rejections (
    id          BIGSERIAL PRIMARY KEY,
    category    TEXT,
    errors      JSONB,
    at          DOUBLE PRECISION
);
