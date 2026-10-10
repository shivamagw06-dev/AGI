-- Intelligence CMS — generic knowledge graph records (Phase 2)
-- Website reads published rows; admin writes via API.

create table if not exists public.intelligence_records (
  id uuid primary key default gen_random_uuid(),
  module text not null,
  status text not null default 'draft'
    check (status in ('draft', 'review', 'published', 'archived')),
  data jsonb not null default '{}'::jsonb,
  detail jsonb not null default '{}'::jsonb,
  relationships jsonb not null default '[]'::jsonb,
  version integer not null default 1,
  created_by text,
  updated_by text,
  published_at timestamptz,
  scheduled_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists intelligence_records_module_status_idx
  on public.intelligence_records (module, status);

create index if not exists intelligence_records_published_at_idx
  on public.intelligence_records (published_at desc nulls last);

create table if not exists public.intelligence_record_versions (
  id uuid primary key default gen_random_uuid(),
  record_id uuid not null references public.intelligence_records(id) on delete cascade,
  version integer not null,
  snapshot jsonb not null,
  changed_by text,
  created_at timestamptz not null default now()
);

create index if not exists intelligence_record_versions_record_idx
  on public.intelligence_record_versions (record_id, version desc);

create table if not exists public.intelligence_relationships (
  id uuid primary key default gen_random_uuid(),
  from_record_id uuid not null references public.intelligence_records(id) on delete cascade,
  to_record_id uuid references public.intelligence_records(id) on delete set null,
  relation_type text not null,
  target_module text,
  target_label text,
  target_ref text,
  created_at timestamptz not null default now()
);

create index if not exists intelligence_relationships_from_idx
  on public.intelligence_relationships (from_record_id);

alter table public.intelligence_records enable row level security;
alter table public.intelligence_record_versions enable row level security;
alter table public.intelligence_relationships enable row level security;

-- Public read: published records only
drop policy if exists intelligence_records_public_read on public.intelligence_records;
create policy intelligence_records_public_read on public.intelligence_records
  for select using (status = 'published');

comment on table public.intelligence_records is 'Intelligence CMS — generic module records (valuation, transactions, firms, etc.)';
