-- AGI persistent research knowledge registry.
-- Additive bridge over KIP/EVE: canonical sources remain immutable in articles;
-- this registry stores validated, queryable intelligence derived from them.

create table if not exists public.research_knowledge_documents (
  id uuid primary key default gen_random_uuid(),
  article_id uuid references public.articles(id) on delete cascade,
  kip_document_id text not null,
  content_hash text not null,
  title text not null,
  slug text,
  author text,
  publisher text,
  publication_date timestamptz,
  document_type text not null default 'agi_research',
  language text not null default 'en',
  source_tier smallint not null default 7 check (source_tier between 1 and 7),
  source_reliability numeric(5,4) not null default 0.7 check (source_reliability between 0 and 1),
  confidence numeric(5,4) not null default 0.5 check (confidence between 0 and 1),
  quality numeric(5,4) not null default 0.5 check (quality between 0 and 1),
  summary text,
  topics jsonb not null default '[]'::jsonb,
  keywords jsonb not null default '[]'::jsonb,
  related_document_ids jsonb not null default '[]'::jsonb,
  pipeline_stages jsonb not null default '[]'::jsonb,
  validation_status text not null default 'pending'
    check (validation_status in ('pending','validated','quarantined','failed','superseded')),
  embedding_version text,
  knowledge_version text,
  source_metadata jsonb not null default '{}'::jsonb,
  validated_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (kip_document_id),
  unique (article_id, content_hash)
);

create table if not exists public.research_knowledge_entities (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.research_knowledge_documents(id) on delete cascade,
  entity_type text not null,
  canonical_name text not null,
  canonical_id text,
  confidence numeric(5,4) not null default 0.7 check (confidence between 0 and 1),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (document_id, entity_type, canonical_name)
);

create table if not exists public.research_knowledge_claims (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.research_knowledge_documents(id) on delete cascade,
  claim_type text not null,
  subject text,
  predicate text,
  object_text text not null,
  stance text not null default 'neutral' check (stance in ('supporting','opposing','neutral','mixed')),
  fact_opinion text not null default 'analysis' check (fact_opinion in ('fact','forecast','opinion','analysis','assumption')),
  time_horizon text,
  effective_date date,
  confidence numeric(5,4) not null default 0.6 check (confidence between 0 and 1),
  source_locator jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.research_knowledge_relationships (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.research_knowledge_documents(id) on delete cascade,
  source_entity text not null,
  relation text not null,
  target_entity text not null,
  confidence numeric(5,4) not null default 0.6 check (confidence between 0 and 1),
  effective_date date,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (document_id, source_entity, relation, target_entity)
);

create table if not exists public.research_knowledge_conflicts (
  id uuid primary key default gen_random_uuid(),
  subject_key text not null,
  claim_a_id uuid not null references public.research_knowledge_claims(id) on delete cascade,
  claim_b_id uuid not null references public.research_knowledge_claims(id) on delete cascade,
  status text not null default 'detected' check (status in ('detected','explained','resolved','dismissed')),
  explanation text,
  resolution_claim_id uuid references public.research_knowledge_claims(id) on delete set null,
  detected_at timestamptz not null default now(),
  resolved_at timestamptz,
  unique (claim_a_id, claim_b_id)
);

create index if not exists research_knowledge_documents_article_idx
  on public.research_knowledge_documents (article_id, publication_date desc);
create index if not exists research_knowledge_documents_validation_idx
  on public.research_knowledge_documents (validation_status, source_tier, publication_date desc);
create index if not exists research_knowledge_entities_lookup_idx
  on public.research_knowledge_entities (canonical_name, entity_type);
create index if not exists research_knowledge_claims_document_idx
  on public.research_knowledge_claims (document_id, claim_type, effective_date desc);
create index if not exists research_knowledge_relationships_lookup_idx
  on public.research_knowledge_relationships (source_entity, relation, target_entity);

alter table public.research_knowledge_documents enable row level security;
alter table public.research_knowledge_entities enable row level security;
alter table public.research_knowledge_claims enable row level security;
alter table public.research_knowledge_relationships enable row level security;
alter table public.research_knowledge_conflicts enable row level security;

comment on table public.research_knowledge_documents is
  'Validated persistent registry linking immutable source articles to KIP intelligence outputs.';

