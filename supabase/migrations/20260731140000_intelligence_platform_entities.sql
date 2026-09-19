-- Intelligence Platform — Universal Entity System (Phase 2.5)

create table if not exists public.intelligence_entities (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  entity_type text not null,
  name text not null,
  description text,
  tags text[] not null default '{}',
  status text not null default 'published'
    check (status in ('draft', 'review', 'published', 'archived')),
  ai_summary text,
  ai_summary_updated_at timestamptz,
  attachments jsonb not null default '[]'::jsonb,
  metadata jsonb not null default '{}'::jsonb,
  source_refs jsonb not null default '[]'::jsonb,
  created_by text,
  updated_by text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists intelligence_entities_type_idx on public.intelligence_entities (entity_type);
create index if not exists intelligence_entities_name_idx on public.intelligence_entities using gin (to_tsvector('english', name));

create table if not exists public.intelligence_entity_relationships (
  id uuid primary key default gen_random_uuid(),
  from_entity_id uuid not null references public.intelligence_entities(id) on delete cascade,
  to_entity_id uuid not null references public.intelligence_entities(id) on delete cascade,
  relation_type text not null,
  label text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (from_entity_id, to_entity_id, relation_type)
);

create index if not exists intelligence_entity_rel_from_idx on public.intelligence_entity_relationships (from_entity_id);
create index if not exists intelligence_entity_rel_to_idx on public.intelligence_entity_relationships (to_entity_id);
create index if not exists intelligence_entity_rel_type_idx on public.intelligence_entity_relationships (relation_type);

create table if not exists public.intelligence_timeline_events (
  id uuid primary key default gen_random_uuid(),
  entity_id uuid not null references public.intelligence_entities(id) on delete cascade,
  event_type text not null,
  title text not null,
  description text,
  occurred_at timestamptz not null,
  source_type text,
  source_id text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists intelligence_timeline_entity_idx on public.intelligence_timeline_events (entity_id, occurred_at desc);

alter table public.intelligence_entities enable row level security;
alter table public.intelligence_entity_relationships enable row level security;
alter table public.intelligence_timeline_events enable row level security;

drop policy if exists intelligence_entities_public_read on public.intelligence_entities;
create policy intelligence_entities_public_read on public.intelligence_entities
  for select using (status = 'published');

comment on table public.intelligence_entities is 'Universal entity registry — companies, firms, funds, people, etc.';
